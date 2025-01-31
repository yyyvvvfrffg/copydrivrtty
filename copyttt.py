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
    print("Requesting access token with data:", data)  # 打印请求数据
    response = requests.post(url, data=data)
    response_data = response.json()
    print("Token Response:", response_data)  # 打印完整的响应
    if "access_token" in response_data:
        return response_data["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response_data}")

# 读取OneDrive的数据
def get_onedrive_data(access_token):
    url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response_data = response.json()
    print("OneDrive Response:", response_data)  # 打印完整的响应
    if "value" in response_data:
        return response_data["value"]
    else:
        raise Exception(f"Failed to get OneDrive data: {response_data}")

# 复制文件到目标OneDrive
def copy_to_target_onedrive(access_token, item, target_drive_id, target_folder_id):
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item['id']}/copy"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = {
        "parentReference": {
            "driveId": target_drive_id,
            "id": target_folder_id
        },
        "name": item["name"]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 202:
        print(f"Starting copy for {item['name']}")
    else:
        print(f"Failed to start copy for {item['name']}: {response.json()}")

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

        target_drive_id = os.getenv("TARGET_DRIVE_ID")
        target_folder_id = os.getenv("TARGET_FOLDER_ID")

        # 检查是否所有环境变量都已设置
        if not all([source_client_id, source_client_secret, source_tenant_id, source_username, source_password]):
            raise Exception("Missing environment variables for source tenant")
        if not all([target_client_id, target_client_secret, target_tenant_id, target_username, target_password, target_drive_id, target_folder_id]):
            raise Exception("Missing environment variables for target tenant")

        print("Source Client ID:", source_client_id)
        print("Target Client ID:", target_client_id)

        # 获取访问令牌
        source_token = get_access_token(source_client_id, source_client_secret, source_tenant_id, source_username, source_password)
        target_token = get_access_token(target_client_id, target_client_secret, target_tenant_id, target_username, target_password)

        # 读取源OneDrive数据
        items = get_onedrive_data(source_token)
        for item in items:
            # 复制到目标OneDrive
            copy_to_target_onedrive(target_token, item, target_drive_id, target_folder_id)

    except Exception as e:
        print("Error:", e)
        raise  # 抛出异常以在 GitHub Actions 中显示
