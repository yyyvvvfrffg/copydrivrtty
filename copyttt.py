import requests
import os

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

# 读取源租户文件夹和文件数据
def get_drive_items(access_token, drive_id):
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response_data = response.json()
    if "value" in response_data:
        return response_data["value"]
    else:
        raise Exception(f"Failed to get drive items: {response_data}")

# 创建或更新目标租户中的文件夹和文件
def create_or_update_drive_item(access_token, drive_id, item_data, parent_id=None):
    if parent_id:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{parent_id}/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=item_data)
    response_data = response.json()
    return response_data

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

        # 假设你有源租户和目标租户的驱动器ID
        source_drive_id = "source_drive_id"
        target_drive_id = "target_drive_id"

        # 读取源租户文件夹和文件数据
        source_items = get_drive_items(source_token, source_drive_id)

        for item in source_items:
            # 递归复制文件夹及其内容
            if item['folder']:
                parent_id = None
                if item['parentReference']:
                    parent_id = item['parentReference']['id']
                create_or_update_drive_item(target_token, target_drive_id, item, parent_id)
            else:
                # 复制文件
                create_or_update_drive_item(target_token, target_drive_id, item)

            print("Item transferred:", item)

    except Exception as e:
        print("Error:", e)
        raise  # 抛出异常以在 GitHub Actions 中显示
