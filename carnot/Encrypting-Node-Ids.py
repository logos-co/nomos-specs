from crypto.PublicKey import RSA
from crypto.Cipher import PKCS1_OAEP

import random

# Function to encrypt and sort the values using distinct public keys
def encrypt_and_sort_values(public_keys, values):
    encrypted_values = []
    for i, value in enumerate(values):
        public_key = public_keys[i]
        cipher = PKCS1_OAEP.new(public_key)
        encrypted_value = cipher.encrypt(value.to_bytes(length=4, byteorder='big'))
        encrypted_values.append(encrypted_value)

    encrypted_values.sort()  # Sort the encrypted values

    return encrypted_values

# Function to retrieve the index of an encrypted value
def get_encrypted_value_index(encrypted_values, target_value):
    for i, encrypted_value in enumerate(encrypted_values):
        if encrypted_value == target_value:
            return i
    return -1

# Main function
def main():
    # Generate a list of random values
    values = [random.randint(1, 10000) for _ in range(500)]
    target_value = random.choice(values)  # Select a random value to find its index
    values.sort()  # Sorting the values
    print(values)
    # Generate distinct RSA public keys

    public_keys = [RSA.generate(2048).publickey() for _ in range(500)]

    # Encrypt and sort the values using distinct public keys
    encrypted_values = encrypt_and_sort_values(public_keys, values)

    print(encrypted_values[3])
    # Retrieve the index of the target encrypted value
    target_index = get_encrypted_value_index(encrypted_values, encrypted_values[3])

    # Output the result
    if target_index != -1:
        print("The index of the target encrypted value is:", target_index)
    else:
        print("The target encrypted value was not found.")



if __name__ == "__main__":
    main()
