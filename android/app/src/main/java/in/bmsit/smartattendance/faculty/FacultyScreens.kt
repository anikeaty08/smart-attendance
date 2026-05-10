package `in`.bmsit.smartattendance.faculty

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.bmsit.smartattendance.ui.components.DashboardList
import `in`.bmsit.smartattendance.ui.components.ThinCard

@Composable
fun FacultyDashboardScreen(token: String, modifier: Modifier = Modifier) {
    val vm: FacultyViewModel = viewModel(factory = FacultyViewModel.Factory(token))
    val state by vm.uiState.collectAsState()

    LaunchedEffect(Unit) {
        vm.refresh()
    }

    Column(modifier = modifier.padding(vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Button(onClick = { vm.refresh() }) { Text("Refresh") }
        ThinCard {
            Text("Start session", fontWeight = FontWeight.SemiBold)
            OutlinedTextField(
                value = state.offeringIdInput,
                onValueChange = vm::onOfferingIdChanged,
                label = { Text("Offering ID") },
            )
            Button(onClick = { vm.startSession() }) { Text("Start lecture") }
            state.lastSession?.let {
                Text("Session #${it.id}")
                Text("Code ${it.code}", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                OutlinedButton(onClick = { vm.endSession() }) { Text("End session") }
            }
        }
        DashboardList(
            "Assigned offerings",
            state.offerings.map { "#${it.id} ${it.subject_code} / ${it.subject_name} / ${it.section}" },
        )
        DashboardList(
            "Attendance report",
            state.report.map { "${it.subject_code}: ${it.present_sessions} present across ${it.total_sessions} sessions (${it.percentage}%)" },
        )
        if (state.status.isNotBlank()) Text(state.status)
    }
}
