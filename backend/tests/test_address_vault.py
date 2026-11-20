import unittest
from bridge_core.address_vault import AddressVaultIntegrityError, EncryptedParticipantAddressCodec

class AddressVaultCodecTests(unittest.TestCase):
    def setUp(self): self.codec=EncryptedParticipantAddressCodec(key=b'k'*32)

    def test_round_trip_and_randomized_ciphertext(self):
        first=self.codec.encrypt(tenant_id='tenant-a',participant_ref='participant-1',address='+15555550123')
        second=self.codec.encrypt(tenant_id='tenant-a',participant_ref='participant-1',address='+15555550123')
        self.assertNotEqual(first,second)
        self.assertEqual(self.codec.decrypt(tenant_id='tenant-a',participant_ref='participant-1',ciphertext=first),'+15555550123')

    def test_ciphertext_is_bound_to_tenant_and_participant_reference(self):
        encrypted=self.codec.encrypt(tenant_id='tenant-a',participant_ref='participant-1',address='+15555550123')
        with self.assertRaises(AddressVaultIntegrityError):
            self.codec.decrypt(tenant_id='tenant-b',participant_ref='participant-1',ciphertext=encrypted)
        with self.assertRaises(AddressVaultIntegrityError):
            self.codec.decrypt(tenant_id='tenant-a',participant_ref='participant-2',ciphertext=encrypted)

    def test_invalid_phone_address_is_rejected_before_encryption(self):
        with self.assertRaises(ValueError):
            self.codec.encrypt(tenant_id='tenant-a',participant_ref='participant-1',address='555-123')

    def test_tampering_is_detected(self):
        encrypted=bytearray(self.codec.encrypt(tenant_id='tenant-a',participant_ref='participant-1',address='+15555550123'))
        encrypted[-1]^=1
        with self.assertRaises(AddressVaultIntegrityError):
            self.codec.decrypt(tenant_id='tenant-a',participant_ref='participant-1',ciphertext=bytes(encrypted))

if __name__=='__main__': unittest.main()
