import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 获取访问令牌
def get_access_token(client_id, client_secret, tenant_id, username, password):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": client_secret,
        "grant_type": "password",
        "username": username,
        "password": password
    }
    response = requests.post(url, data=data)
    response_data = response.json()
    if "access_token" in response_data:
        return response_data["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response_data}")

# 获取驱动器列表
def get_drives(access_token):
    url = "https://graph.microsoft.com/v1.0/me/drives"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response_data = response.json()
    if "value" in response_data:
        return response_data["value"]
    else:
        raise Exception(f"Failed to get drives: {response_data}")

# 读取文件夹和文件数据
def get_drive_items(access_token, drive_id, parent_id=None):
    if parent_id:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response_data = response.json()
    if "value" in response_data:
        return response_data["value"]
    else:
        raise Exception(f"Failed to get drive items: {response_data}")

# 下载文件内容
def download_file(download_url):
    response = requests.get(download_url)
    return response.content

# 上传文件到目标租户
def upload_file(access_token, drive_id, parent_id, file_name, file_content):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}:/{file_name}:/content"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/octet-stream"}
    response = requests.put(url, headers=headers, data=file_content)
    response_data = response.json()
    return response_data

# 创建文件夹到目标租户
def create_folder(access_token, drive_id, parent_id, folder_name, max_retries=5):
    if not parent_id:
        parent_id = 'root'  # 如果没有parent_id，则默认创建在根目录
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}/children"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    folder_data = {
        "name": folder_name,
        "folder": {}
    }
    retry_count = 0
    while retry_count < max_retries:
        response = requests.post(url, headers=headers, json=folder_data)
        response_data = response.json()
        print(f"Create folder response (attempt {retry_count+1}): {response_data}")  # 打印API响应以调试
        if 'id' in response_data:
            return response_data
        elif response_data['error']['code'] == 'nameAlreadyExists':
            print(f"Folder {folder_name} already exists. Skipping creation.")
            existing_folder = get_existing_folder_id(access_token, drive_id, parent_id, folder_name)
            if existing_folder:
                return existing_folder
            raise Exception(f"Failed to find existing folder: {response_data}")
        elif response_data['error']['code'] == 'activityLimitReached':
            retry_count += 1
            wait_time = 180  # 3 minutes
            print(f"Activity limit reached. Waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
        else:
            print(f"Failed to create folder: {folder_data}")
            print(f"Response: {response_data}")
            retry_count += 1
            wait_time = 180  # 3 minutes
            print(f"Error occurred. Waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
    raise Exception(f"Failed to create folder after {max_retries} attempts: {response_data}")

# 获取已存在文件夹的ID
def get_existing_folder_id(access_token, drive_id, parent_id, folder_name):
    items = get_drive_items(access_token, drive_id, parent_id)
    for item in items:
        if item['name'] == folder_name and 'folder' in item:
            return item
    return None

# 删除文件或文件夹
def delete_item(access_token, drive_id, item_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.delete(url, headers=headers)
    if response.status_code == 204:
        print(f"Item {item_id} deleted successfully.")
    else:
        print(f"Failed to delete item {item_id}: {response.status_code}, {response.text}")

# 处理单个项目的复制和删除
def process_item(source_token, target_token, source_drive_id, target_drive_id, item, target_parent_id):
    try:
        if 'folder' in item:
            # 创建文件夹
            folder_name = item['name']
            created_folder = create_folder(target_token, target_drive_id, target_parent_id, folder_name)
            if 'id' not in created_folder:
                raise KeyError(f"Created folder response does not contain 'id': {created_folder}")
            # 递归复制文件夹内容
            copy_folder_contents(source_token, target_token, source_drive_id, target_drive_id, item['id'], created_folder['id'])
            # 删除源文件夹
            delete_item(source_token, source_drive_id, item['id'])
        else:
            # 下载文件内容
            file_content = download_file(item['@microsoft.graph.downloadUrl'])
            file_name = item['name']
            # 上传文件到目标租户
            upload_file(target_token, target_drive_id, target_parent_id, file_name, file_content)
            print(f"File uploaded: {file_name}")
            # 删除源文件
            delete_item(source_token, source_drive_id, item['id'])
    except Exception as e:
        print(f"Error processing item {item['name']}: {e}")

# 递归复制文件夹及其内容，并删除源文件
def copy_folder_contents(source_token, target_token, source_drive_id, target_drive_id, source_parent_id, target_parent_id):
    items = get_drive_items(source_token, source_drive_id, source_parent_id)
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [
            executor.submit(process_item, source_token, target_token, source_drive_id, target_drive_id, item, target_parent_id)
            for item in items
        ]
        for future in as_completed(futures):
            future.result()

# 主逻辑
if __name__ == "__main__":
    while True:
        try:
            # 从环境变量中获取参数
            source_client_id = os.getenv("SOURCE_CLIENT_ID")
            source_client_secret = os.getenv("SOURCE_CLIENT_SECRET")
            source_tenant_id = os.getenv("SOURCE_TENANT_ID")
            source_username = os.getenv("SOURCE_USERNAME")
            source_password = os.getenv("SOURCE_PASSWORD")

            target_client_id = os.getenv("TARGET_CLIENT_ID")
            target_client_secret = os.getenv("TARGET_CLIENT_SECRET")
            target_tenant_id = os.getenv("TARGET_TENANT_ID")
            target_username = os.getenv("TARGET_USERNAME")
            target_password = os.getenv("TARGET_PASSWORD")

            # 获取访问令牌
            source_token = get_access_token(source_client_id, source_client_secret, source_tenant_id, source_username, source_password)
            target_token = get_access_token(target_client_id, target_client_secret, target_tenant_id, target_username, target_password)

            # 获取源租户和目标租户的驱动器 ID
            source_drives = get_drives(source_token)
            target_drives = get_drives(target_token)

            source_drive_id = source_drives[0]['id']  # 假设我们使用第一个驱动器
            target_drive_id = target_drives[0]['id']  # 假设我们使用第一个驱动器

            # 递归复制源租户的根文件夹内容到目标租户的根文件夹
            copy_folder_contents(source_token, target_token, source_drive_id, target_drive_id, None, None)

        except Exception as e:
            print("Error:", e)
            # 等待3分钟后重试
            wait_time = 180  # 3分钟
            print(f"An error occurred. Waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            continue  # 继续循环，重试操作
