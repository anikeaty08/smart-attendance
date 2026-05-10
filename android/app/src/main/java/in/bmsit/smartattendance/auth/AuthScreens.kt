package `in`.bmsit.smartattendance.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.bmsit.smartattendance.ui.components.ThinCard

@Composable
fun AuthScreen(
    viewModel: AuthViewModel,
    modifier: Modifier = Modifier,
    onAuthenticated: () -> Unit = {},
) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        ThinCard {
            Text("College sign-in token", fontWeight = FontWeight.SemiBold)
            Text(
                "Paste the session token issued after Clerk login (campus SSO). Tokens are stored securely on this device.",
                color = Color(0xFF666666),
            )
            OutlinedTextField(
                value = state.tokenInput,
                onValueChange = viewModel::onTokenChanged,
                label = { Text("Bearer session token") },
                modifier = Modifier.fillMaxWidth(),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { viewModel.login() }, enabled = state.tokenInput.isNotBlank() && !state.loading) {
                    Text(if (state.loading) "Signing in..." else "Continue")
                }
            }
            if (state.status.isNotBlank()) {
                Text(state.status, color = Color(0xFFB42318))
            }
            Text(
                "Tip: your web portal can redirect to smartattendance://auth?session_token=&lt;jwt&gt; to open the app prefilled.",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF666666),
            )
        }
    }
}

@Composable
fun FirstLoginScreen(token: String, onVerified: () -> Unit, modifier: Modifier = Modifier) {
    val vm: FirstLoginViewModel = viewModel(factory = FirstLoginViewModel.Factory(token))
    val state by vm.state.collectAsState()
    Column(modifier = modifier) {
        ThinCard {
            Text("Verify first login", fontWeight = FontWeight.SemiBold)
            Text("Verify the OTP sent to your institute email.", color = Color(0xFF666666))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    enabled = !state.sending,
                    onClick = { vm.sendOtp() },
                ) { Text(if (state.sending) "Sending..." else "Send OTP") }
                OutlinedTextField(value = state.otpInput, onValueChange = vm::onOtpChange, label = { Text("OTP") })
            }
            Button(
                enabled = state.otpInput.length == 6 && !state.verifying,
                onClick = { vm.verify(onVerified) },
            ) {
                Text(if (state.verifying) "Verifying..." else "Verify")
            }
            if (state.status.isNotBlank()) Text(state.status)
        }
    }
}
