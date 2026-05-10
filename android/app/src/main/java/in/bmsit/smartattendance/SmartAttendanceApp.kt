package `in`.bmsit.smartattendance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import `in`.bmsit.smartattendance.auth.AuthScreen
import `in`.bmsit.smartattendance.auth.AuthViewModel
import `in`.bmsit.smartattendance.auth.FirstLoginScreen
import `in`.bmsit.smartattendance.faculty.FacultyDashboardScreen
import `in`.bmsit.smartattendance.student.StudentDashboardScreen
import `in`.bmsit.smartattendance.ui.components.BrandHeader

@Composable
fun SmartAttendanceApp(authViewModel: AuthViewModel, modifier: Modifier = Modifier) {
    val auth by authViewModel.uiState.collectAsState()
    MaterialTheme {
        Surface(modifier = modifier.fillMaxSize(), color = Color(0xFFF8F8F4)) {
            Column(
                modifier = Modifier.fillMaxSize().padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                BrandHeader()
                when (val user = auth.user) {
                    null -> AuthScreen(authViewModel, modifier = Modifier)
                    else -> {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${user.name} / ${user.role}", fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                            OutlinedButton(onClick = { authViewModel.logout() }) { Text("Sign out") }
                        }
                        val pendingStaffVerification = !user.first_login_verified && user.role != "student"
                        if (pendingStaffVerification) {
                            FirstLoginScreen(token = auth.tokenInput, onVerified = { authViewModel.refreshMe() })
                        } else {
                            when (user.role) {
                                "student" -> StudentDashboardScreen(token = auth.tokenInput, modifier = Modifier.fillMaxWidth())
                                else -> FacultyDashboardScreen(token = auth.tokenInput, modifier = Modifier.fillMaxWidth())
                            }
                        }
                    }
                }
            }
        }
    }
}
