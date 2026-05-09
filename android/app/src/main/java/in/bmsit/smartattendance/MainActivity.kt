package in.bmsit.smartattendance

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import in.bmsit.smartattendance.ui.ActiveSession
import in.bmsit.smartattendance.ui.FacultyOffering
import in.bmsit.smartattendance.ui.StudentSubject

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    SmartAttendanceApp()
                }
            }
        }
    }
}

@Composable
fun SmartAttendanceApp() {
    var role by remember { mutableStateOf("student") }
    var email by remember { mutableStateOf("student1@student.bmsit.in") }
    Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Smart Attendance", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        LoginPanel(email = email, role = role, onEmailChange = { email = it }, onRoleChange = { role = it })
        if (role == "student") StudentDashboard() else FacultyDashboard()
    }
}

@Composable
fun LoginPanel(email: String, role: String, onEmailChange: (String) -> Unit, onRoleChange: (String) -> Unit) {
    Card {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("College Mail Login", fontWeight = FontWeight.SemiBold)
            OutlinedTextField(value = email, onValueChange = onEmailChange, label = { Text("BMSIT email") }, modifier = Modifier.fillMaxWidth())
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { onRoleChange("student") }, enabled = role != "student") { Text("Student") }
                Button(onClick = { onRoleChange("faculty") }, enabled = role != "faculty") { Text("Faculty") }
            }
        }
    }
}

@Composable
fun StudentDashboard() {
    val sessions = listOf(
        ActiveSession(1, "BCS401", "Database Management Systems", "Demo Faculty", "Lecture", "Ends in 05:00")
    )
    val subjects = listOf(
        StudentSubject("BCS401", "Database Management Systems", "Demo Faculty", 86.5),
    )
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Active Attendance", style = MaterialTheme.typography.titleLarge)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.height(140.dp)) {
            items(sessions) { session ->
                Card {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("${session.subjectCode} · ${session.subjectName}", fontWeight = FontWeight.SemiBold)
                        Text("${session.facultyName} · ${session.sessionType} · ${session.endsIn}")
                        Button(onClick = { }) { Text("Enter 4-digit code") }
                    }
                }
            }
        }
        Text("My Enrolled Subjects", style = MaterialTheme.typography.titleLarge)
        subjects.forEach { subject ->
            Card {
                Row(modifier = Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("${subject.subjectCode} · ${subject.subjectName}", fontWeight = FontWeight.SemiBold)
                        Text(subject.facultyName)
                    }
                    Text("${subject.attendancePercent}%")
                }
            }
        }
    }
}

@Composable
fun FacultyDashboard() {
    val offerings = listOf(
        FacultyOffering(1, "BCS401", "Database Management Systems", "4th Sem A")
    )
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Text("Assigned Classes", style = MaterialTheme.typography.titleLarge)
        offerings.forEach { offering ->
            Card {
                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("${offering.subjectCode} · ${offering.subjectName}", fontWeight = FontWeight.SemiBold)
                    Text(offering.section)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { }) { Text("Start Lecture") }
                        Button(onClick = { }) { Text("View Sessions") }
                    }
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        Text("Start session flow captures faculty location, creates a 4-digit code, and opens a live attendance count.")
    }
}

