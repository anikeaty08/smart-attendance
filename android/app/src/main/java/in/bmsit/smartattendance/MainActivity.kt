package `in`.bmsit.smartattendance

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.ViewModelProvider
import `in`.bmsit.smartattendance.auth.AuthViewModel
import `in`.bmsit.smartattendance.auth.SessionStore

class MainActivity : ComponentActivity() {
    private lateinit var sessionStore: SessionStore
    private lateinit var authViewModel: AuthViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        sessionStore = SessionStore(this)
        authViewModel = ViewModelProvider(this, AuthViewModel.Factory(sessionStore))[AuthViewModel::class.java]

        setContent {
            SmartAttendanceApp(authViewModel = authViewModel)
        }
        handleAuthIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleAuthIntent(intent)
    }

    private fun handleAuthIntent(intent: Intent?) {
        val uri: Uri = intent?.data ?: return
        if (uri.scheme != "smartattendance" || uri.host != "auth") return
        val token = uri.getQueryParameter("session_token") ?: uri.getQueryParameter("token") ?: return
        authViewModel.applyIncomingSessionToken(token)
    }
}
