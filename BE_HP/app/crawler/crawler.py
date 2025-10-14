import requests
from datetime import datetime
from ..models.log_schemas import LogType
from ..routes.logs.log_utils import insert_log
import os
from dotenv import load_dotenv

load_dotenv() 

class DataCrawler:

    def __init__(self): 
        self.base_url = os.getenv('DATA_API_URL') 
        self.username = os.getenv('USR_NAME')
        self.password = os.getenv('PWR')

        self.token = None
        self.token_expiry = None

    def _get_token(self): 
        try: 
            login_url = f'{self.base_url}/api/user/login'
            insert_log(f"Đang login để lấy token từ {login_url}", LogType.INFO)
            
            response = requests.post(
                login_url, 
                json={"Username":self.username, 'Password':self.password},
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            self.token = data.get("access_token")
            expiry_seconds = data.get('expires_in', 3600)
            self.token_expiry = datetime.now().timestamp() + expiry_seconds

            token_expires_at = datetime.fromtimestamp(self.token_expiry)
            insert_log(f"Lấy thành công token cho api cào dữ liệu. Token hết hạn lúc: {token_expires_at.strftime('%Y-%m-%d %H:%M:%S')}", LogType.INFO)
            return True

        except requests.exceptions.HTTPError as e:
            insert_log(f"HTTP Error khi login: {e.response.status_code} - {e.response.text}", LogType.ERROR)
            return False
        except requests.exceptions.Timeout as e:
            insert_log(f"Timeout khi login: {str(e)}", LogType.ERROR)
            return False
        except Exception as e:
            insert_log(f"Lỗi không xác định khi lấy token: {str(e)}", LogType.ERROR)
            return False
    
    def ensure_token(self):
        current_time = datetime.now().timestamp()
        
        if not self.token or not self.token_expiry:
            insert_log("Không có token, cần lấy token mới", LogType.INFO)
            return self._get_token()
        
        time_buffer = 300  
        if current_time >= (self.token_expiry - time_buffer):
            insert_log(f"Token sắp hết hạn (còn {(self.token_expiry - current_time)/60:.1f} phút), refresh token", LogType.INFO)
            return self._get_token()
        
        remaining_time = (self.token_expiry - current_time) / 60
        insert_log(f"Token còn hiệu lực {remaining_time:.1f} phút", LogType.INFO)
        return True
    
    def request(self, method, endpoint, **kwargs):
        if not self.ensure_token():
            raise Exception("Không lấy được token xác thực")
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        kwargs['headers'] = headers
        
        params = kwargs.get('params', {})
        insert_log(f"Gọi API {method} {endpoint} với params: {params}", LogType.INFO)
        
        try:
            response = requests.request(method, url, **kwargs)
            insert_log(f"API response status: {response.status_code}", LogType.INFO)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            insert_log(f"HTTP Error {response.status_code} cho API {endpoint}: {response.text}", LogType.ERROR)
            
            if response.status_code in [401, 400]:
                if response.status_code == 401:
                    insert_log("401 Unauthorized - Token hết hạn, thử refresh token...", LogType.WARNING)
                elif response.status_code == 400 and "token" in response.text.lower():
                    insert_log("400 Bad Request có thể do token issue, thử refresh token...", LogType.WARNING)
                else:
                    raise
                
                if self._get_token():
                    insert_log("Token refresh thành công, thử gọi API lại...", LogType.INFO)
                    kwargs['headers']['Authorization'] = f"Bearer {self.token}"
                    retry_response = requests.request(method, url, **kwargs)
                    insert_log(f"Retry API response status: {retry_response.status_code}", LogType.INFO)
                    retry_response.raise_for_status()
                    return retry_response.json()
                else:
                    insert_log("Không thể refresh token", LogType.ERROR)
            
            raise
            
        except requests.exceptions.Timeout as e:
            insert_log(f"Timeout khi gọi API {endpoint}: {str(e)}", LogType.ERROR)
            raise
            
        except requests.exceptions.ConnectionError as e:
            insert_log(f"Connection error khi gọi API {endpoint}: {str(e)}", LogType.ERROR)
            raise
            
        except Exception as e:
            insert_log(f"Lỗi không xác định khi gọi API {endpoint}: {str(e)}", LogType.ERROR)
            raise

api_client = DataCrawler()