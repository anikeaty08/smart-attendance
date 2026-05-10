package `in`.bmsit.smartattendance.student

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.bmsit.smartattendance.location.LocationRepository
import `in`.bmsit.smartattendance.ui.components.DashboardList
import `in`.bmsit.smartattendance.ui.components.ThinCard

@Composable
fun StudentDashboardScreen(token: String, modifier: Modifier = Modifier) {
    val locationRepo = remember { LocationRepository() }
    val vm: StudentViewModel = viewModel(factory = StudentViewModel.Factory(token, locationRepo))
    val state by vm.uiState.collectAsState()
    val context = LocalContext.current

    var permissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED,
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(contract = ActivityResultContracts.RequestPermission()) { granted ->
        permissionGranted = granted
        vm.refresh()
    }

    LaunchedEffect(Unit) {
        vm.refresh()
    }

    Column(modifier = modifier.padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = { vm.refresh() }) { Text("Refresh") }
            OutlinedButton(onClick = { vm.requestLeave() }) { Text("Request Leave") }
        }
        if (!permissionGranted) {
            Text("Location permission is required for attendance marking.", color = Color(0xFFB42318))
            Button(onClick = { permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION) }) {
                Text("Grant location permission")
            }
        }
        if (state.alerts.isNotEmpty()) {
            ThinCard {
                Text("Attendance alerts", fontWeight = FontWeight.SemiBold)
                state.alerts.forEach { Text("${it.subject_code}: ${it.percentage}% / ${it.level}") }
            }
        }
        ThinCard {
            Text("Active sessions", fontWeight = FontWeight.SemiBold)
            if (state.sessions.isEmpty()) {
                Text("No active sessions. Tap refresh.", color = Color(0xFF666666))
            } else {
                state.sessions.forEach { session ->
                    val selected = state.selectedSessionId == session.id
                    OutlinedButton(onClick = { vm.selectSession(session.id) }) {
                        val marker = if (selected) "[Selected] " else ""
                        Text("${marker}#${session.id} ${session.subject_code} / ${session.session_type} / ${session.radius_meters}m")
                    }
                }
            }
            OutlinedTextField(
                value = state.codeInput,
                onValueChange = vm::onCodeChanged,
                label = { Text("4-digit code") },
            )
            Button(
                onClick = {
                    if (!permissionGranted) {
                        permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                    } else {
                        vm.markAttendance(context)
                    }
                },
                enabled = !state.submitting && !state.loading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (state.submitting) "Marking..." else "Mark attendance")
            }
        }
        DashboardList(
            "My enrolled subjects",
            state.subjects.map { "${it.subject_code} / ${it.subject_name} / ${it.faculty_name}" },
        )
        DashboardList(
            "Attendance summary",
            state.summaries.map { "${it.subject_code}: ${it.present_sessions}/${it.total_sessions} (${it.percentage}%)" },
        )
        if (state.loading) Text("Loading…")
        if (state.status.isNotBlank()) Text(state.status)
    }
}
