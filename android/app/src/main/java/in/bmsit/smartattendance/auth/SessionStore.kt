package `in`.bmsit.smartattendance.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class SessionStore(context: Context) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "secure_session",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun saveToken(token: String) {
        prefs.edit().putString(KEY_BEARER_TOKEN, token).apply()
    }

    fun token(): String = prefs.getString(KEY_BEARER_TOKEN, "") ?: ""

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_BEARER_TOKEN = "bearer_token"
    }
}
