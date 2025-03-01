import CryptoJS from 'crypto-js';

// Function to derive a key from a passphrase (simplified - passphrase is directly used as key)
export const deriveKey = (passphrase: string) => {
    // Directly use the passphrase to create a CryptoJS WordArray key
    const key = CryptoJS.SHA256(passphrase).toString(); // Using SHA256 to hash passphrase to key
    console.log("Derived Key (Frontend, Hex):", key); // Log derived key in hex format
    return CryptoJS.enc.Hex.parse(key); // Return parsed key
};

// Function to encrypt data (simplified - no IV or salt)
export const encryptData = (data: string, key: CryptoJS.lib.WordArray) => {
    const encrypted = CryptoJS.AES.encrypt(data, key, {
        mode: CryptoJS.mode.ECB, // Using ECB mode - simpler, but less secure
        padding: CryptoJS.pad.Pkcs7
    });
    return encrypted.ciphertext.toString(CryptoJS.enc.Base64); // Return only ciphertext in Base64
};

// Function to decrypt data (simplified - no IV or salt)
export const decryptData = (encryptedData: string, key: CryptoJS.lib.WordArray) => {
    try {
        const ciphertext = CryptoJS.enc.Base64.parse(encryptedData);

        const decrypted = CryptoJS.AES.decrypt({ ciphertext: ciphertext } as CryptoJS.lib.CipherParams, key, {
            mode: CryptoJS.mode.ECB, // ECB mode for decryption as well
            padding: CryptoJS.pad.Pkcs7,
        });

        return decrypted.toString(CryptoJS.enc.Utf8);
    } catch (error) {
        console.error("Decryption error:", error);
        throw error; // Or handle error as needed
    }
}; 