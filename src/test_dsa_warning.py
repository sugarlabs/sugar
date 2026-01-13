def test_dsa_warning():
    key_type = "ssh-dss"
    if key_type == "ssh-dss":
        print(
            "WARNING: Your SSH key type (DSA) is unsupported. "
            "Please generate RSA or ED25519 key."
        )

if __name__ == "__main__":
    test_dsa_warning()
