import os
from google.oauth2 import service_account
from google.cloud import storage
class StorageClientWrapper:
    def __init__(self):

        self.bucket_name = "authentic_scope_docs"
        self.object_name = ""
        self.credential_path = os.path.join(os.path.dirname(__file__), "sa.json")
        self.storage_client = self.create_storage_client(self.credential_path)

    @staticmethod
    def create_storage_client(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        return storage.Client(credentials=credentials)

    def upload_file(self, file_name, file_path):

        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(file_name)
        blob.upload_from_filename(file_path)
        print(f"File {file_path} uploaded to {self.bucket_name}/{self.object_name}")

    def list_files(self):
        bucket = self.storage_client.bucket(self.bucket_name)
        blobs = bucket.list_blobs()

        file_names = [blob.name for blob in blobs]

        return file_names