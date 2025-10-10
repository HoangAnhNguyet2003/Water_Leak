import requests
from datetime import datetime
from ..extensions import get_db
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

            insert_log(f"Lấy thành công token cho api cào dữ liệu", LogType.INFO)
            return True

        except Exception as e:
            insert_log(f"Lỗi khi lấy token: {str(e)}", LogType.ERROR)
            return False
    
    def ensure_token(self):
        if (not self.token or 
                not self.token_expiry or 
                datetime.now().timestamp() >= self.token_expiry):
            return self._get_token()
        return True
    
    def request(self, method, endpoint, **kwargs):
        if not self.ensure_token():
            raise Exception("Không lấy được token xác thực")
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.token}"
        kwargs['headers'] = headers
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                if self._get_token():
                    kwargs['headers']['Authorization'] = f"Bearer {self.token}"
                    response = requests.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response.json()
            raise
        except Exception as e:
            insert_log(f"Lỗi khi gọi API {endpoint}: {str(e)}", LogType.ERROR)
            raise

api_client = DataCrawler()