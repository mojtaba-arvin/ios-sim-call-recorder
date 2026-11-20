import tempfile, unittest
from pathlib import Path
from uuid import uuid4
from bridge_core.object_storage import S3MediaObjectStore

class FakeS3:
    def __init__(self): self.upload=None; self.deleted=None; self.download=None; self.presign=None
    def upload_file(self,filename,bucket,key,ExtraArgs): self.upload=(filename,bucket,key,ExtraArgs)
    def download_file(self,bucket,key,filename): self.download=(bucket,key,filename)
    def delete_object(self,**kwargs): self.deleted=kwargs
    def generate_presigned_url(self,operation,Params,ExpiresIn): self.presign=(operation,Params,ExpiresIn); return 'https://example.invalid/signed'

def wav(path):
    import struct
    samples=b'\0\0'*16000
    fmt=struct.pack('<HHIIHH',1,1,16000,32000,2,16)
    body=b'WAVE'+b'fmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(samples))+samples
    path.write_bytes(b'RIFF'+struct.pack('<I',len(body))+body)

class S3MediaObjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.client=FakeS3()
        self.store=S3MediaObjectStore(client=self.client,bucket='private-recordings',kms_key_id='alias/test-media')
        self.tenant='tenant-private'
        self.session=str(uuid4())
        self.media=str(uuid4())

    def test_upload_validates_and_uses_kms_encryption(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'test.wav'; wav(source)
            result=self.store.put_wav(tenant_id=self.tenant,session_id=self.session,media_id=self.media,source_path=source)
            self.assertEqual(result.channel_count,1)
            self.assertEqual(self.client.upload[1],'private-recordings')
            self.assertEqual(self.client.upload[3]['ServerSideEncryption'],'aws:kms')
            self.assertEqual(self.client.upload[3]['SSEKMSKeyId'],'alias/test-media')
            self.assertNotIn(self.tenant,result.object_key)

    def test_download_delete_and_short_lived_presign_are_tenant_scoped(self):
        self.store.download_wav(tenant_id=self.tenant,session_id=self.session,media_id=self.media,destination_path='/tmp/out.wav')
        self.assertIn(self.session,self.client.download[1])
        self.store.delete(tenant_id=self.tenant,session_id=self.session,media_id=self.media)
        self.assertEqual(self.client.deleted['Key'],self.client.download[1])
        url=self.store.presigned_download_url(tenant_id=self.tenant,session_id=self.session,media_id=self.media,expires_seconds=120)
        self.assertTrue(url.startswith('https://'))
        self.assertEqual(self.client.presign[2],120)

    def test_invalid_ids_and_long_presign_lifetime_are_rejected(self):
        with self.assertRaises(ValueError): self.store.delete(tenant_id=self.tenant,session_id='../../x',media_id=self.media)
        with self.assertRaises(ValueError): self.store.presigned_download_url(tenant_id=self.tenant,session_id=self.session,media_id=self.media,expires_seconds=301)

if __name__=='__main__': unittest.main()
