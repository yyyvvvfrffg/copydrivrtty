import requests
import os
import time

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
def create_folder(access_token, drive_id, parent_id, folder_name, retries=3):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}/children"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    folder_data = {
        "name": folder_name,
        "folder": {}
    }
    for attempt in range(retries):
        response = requests.post(url, headers=headers, json=folder_data)
        response_data = response.json()
        print(f"Create folder response (attempt {attempt+1}): {response_data}")  # 打印API响应以调试
        if 'id' in response_data:
            return response_data
        elif attempt < retries - 1:
            time.sleep(2 ** attempt)  # 指数退避重试
        else:
            # 打印详细的错误信息
            print(f"Failed to create folder: {folder_data}")
            print(f"Response: {response_data}")
            raise Exception(f"Failed to create folder after {retries} attempts: {response_data}")

# 递归复制文件夹及其内容
def copy_folder_contents(source_token, target_token, source_drive_id, target_drive_id, source_parent_id, target_parent_id):
    items = get_drive_items(source_token, source_drive_id, source_parent_id)
    for item in items:
        if 'folder' in item:
            # 创建文件夹
            folder_name = item['name']
            created_folder = create_folder(target_token, target_drive_id, target_parent_id, folder_name)
            if 'id' not in created_folder:
                raise KeyError(f"Created folder response does not contain 'id': {created_folder}")
            # 递归复制文件夹内容
            copy_folder_contents(source_token, target_token, source_drive_id, target_drive_id, item['id'], created_folder['id'])
        else:
            # 下载文件内容
            file_content = download_file(item['@microsoft.graph.downloadUrl'])
            file_name = item['name']
            # 上传文件到目标租户
            upload_file(target_token, target_drive_id, target_parent_id, file_name, file_content)
            print(f"File uploaded: {file_name}")

# 主逻辑
if __name__ == "__main__":
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
        raise  # 抛出异常以在 GitHub Actions 中显示
