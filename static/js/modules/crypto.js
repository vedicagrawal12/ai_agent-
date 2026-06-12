/**
 * LeadHunter AI — Crypto Helper Module
 * Uses native Web Crypto API (AES-GCM) to encrypt/decrypt strings.
 */

export const CryptoHelper = {
    async _getKey(rawKey) {
        const enc = new TextEncoder();
        // Ensure rawKey is formatted correctly (32 bytes for AES-256)
        const keyData = enc.encode(rawKey.padEnd(32, '0').slice(0, 32));
        return await window.crypto.subtle.importKey(
            "raw",
            keyData,
            "AES-GCM",
            true,
            ["encrypt", "decrypt"]
        );
    },

    async encrypt(text, rawKey) {
        if (!text || !rawKey) return text;
        try {
            const key = await this._getKey(rawKey);
            const enc = new TextEncoder();
            const iv = window.crypto.getRandomValues(new Uint8Array(12));
            const ciphertext = await window.crypto.subtle.encrypt(
                { name: "AES-GCM", iv: iv },
                key,
                enc.encode(text)
            );
            
            // Combine IV and ciphertext for storage, then convert to Base64
            const combined = new Uint8Array(iv.length + ciphertext.byteLength);
            combined.set(iv, 0);
            combined.set(new Uint8Array(ciphertext), iv.length);
            
            return btoa(Array.from(combined).map(b => String.fromCharCode(b)).join(''));
        } catch (e) {
            console.error("Encryption failed:", e);
            return text;
        }
    },

    async decrypt(ciphertextBase64, rawKey) {
        if (!ciphertextBase64 || !rawKey) return ciphertextBase64;
        
        // Simple check to determine if the string is likely encrypted
        // Our Base64 payload will always be at least 12 bytes IV + data
        if (ciphertextBase64.length < 16) {
            return ciphertextBase64;
        }
        
        try {
            const key = await this._getKey(rawKey);
            const binaryString = atob(ciphertextBase64);
            const combined = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                combined[i] = binaryString.charCodeAt(i);
            }
            
            const iv = combined.slice(0, 12);
            const data = combined.slice(12);
            
            const decrypted = await window.crypto.subtle.decrypt(
                { name: "AES-GCM", iv: iv },
                key,
                data
            );
            
            const dec = new TextDecoder();
            return dec.decode(decrypted);
        } catch (e) {
            // If decryption fails, it might be an unencrypted legacy string
            // Log it but return original string as a safe fallback
            console.warn("Decryption failed (could be legacy unencrypted key):", e);
            return ciphertextBase64;
        }
    }
};
