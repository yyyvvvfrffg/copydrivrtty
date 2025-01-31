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

# 读取源租户数据
def get_users(access_token):
    url = "https://graph.microsoft.com/v1.0/users"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response_data = response.json()
    print("Users Response:", response_data)  # 打印完整的响应
    if "value" in response_data:
        return response_data["value"]
    else:
        raise Exception(f"Failed to get users: {response_data}")

# 写入目标租户数据
def create_user(access_token, user_data):
    url = "https://graph.microsoft.com/v1.0/users"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    
    # 删除用户数据中的邮件字段
    user_data.pop('mail', None)
    
    response = requests.post(url, headers=headers, json=user_data)
    print(f"Creating user: {user_data['displayName']} - Response: {response.json()}")  # 打印创建用户的响应
    return response.json()

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

        # 检查是否所有环境变量都已设置
        if not all([source_client_id, source_client_secret, source_tenant_id, source_username, source_password]):
            raise Exception("Missing environment variables for source tenant")
        if not all([target_client_id, target_client_secret, target_tenant_id, target_username, target_password]):
            raise Exception("Missing environment variables for target tenant")

        print("Source Client ID:", source_client_id)
        print("Target Client ID:", target_client_id)

        # 获取访问令牌
        source_token = get_access_token(source_client_id, source_client_secret, source_tenant_id, source_username, source_password)
        target_token = get_access_token(target_client_id, target_client_secret, target_tenant_id, target_username, target_password)

        # 读取源租户用户数据
        users = get_users(source_token)
        for user in users:
            # 创建用户到目标租户
            user_data = {
                "accountEnabled": True,
                "displayName": user["displayName"],
                "mailNickname": user.get("mailNickname", ""),
                "userPrincipalName": user["userPrincipalName"],
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": True,
                    "password": "your_password"
                }
            }
            create_user(target_token, user_data)

    except Exception as e:
        print("Error:", e)
        raise  # 抛出异常以在 GitHub Actions 中显示
