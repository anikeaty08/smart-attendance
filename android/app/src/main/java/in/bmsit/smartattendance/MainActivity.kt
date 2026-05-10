package in.bmsit.smartattendance

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.LocationServices
import in.bmsit.smartattendance.network.ActiveSessionDto
import in.bmsit.smartattendance.network.ApiClient
import in.bmsit.smartattendance.network.AttendanceAlertDto
import in.bmsit.smartattendance.network.AttendanceSummaryDto
import in.bmsit.smartattendance.network.CreateCondonationRequest
import in.bmsit.smartattendance.network.CreateLeaveRequest
import in.bmsit.smartattendance.network.FirstLoginOtpVerifyRequest
import in.bmsit.smartattendance.network.MeResponse
import in.bmsit.smartattendance.network.StartSessionRequest
import in.bmsit.smartattendance.network.StartSessionResponse
import in.bmsit.smartattendance.network.SubjectOfferingDto
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import org.json.JSONObject
import retrofit2.HttpException
import kotlin.coroutines.resume

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFFF8F8F4)) {
                    SmartAttendanceApp()
                }
            }
        }
    }
}

private data class DeviceLocation(val latitude: Double, val longitude: Double, val accuracyMeters: Double)

private fun hasLocationPermission(context: Context): Boolean {
    return ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
}

private fun isLocationEnabled(context: Context): Boolean {
    val manager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager ?: return false
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
        manager.isLocationEnabled
    } else {
        manager.isProviderEnabled(LocationManager.GPS_PROVIDER) || manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
    }
}

private suspend fun fetchCurrentLocation(context: Context): DeviceLocation? = suspendCancellableCoroutine { continuation ->
    val locationClient = LocationServices.getFusedLocationProviderClient(context)
    val request = CurrentLocationRequest.Builder()
        .setDurationMillis(8000)
        .setMaxUpdateAgeMillis(3000)
        .build()
    locationClient
        .getCurrentLocation(request, null)
        .addOnSuccessListener { location ->
            if (!continuation.isActive) return@addOnSuccessListener
            if (location == null) {
                continuation.resume(null)
                return@addOnSuccessListener
            }
            continuation.resume(
                DeviceLocation(
                    latitude = location.latitude,
                    longitude = location.longitude,
                    accuracyMeters = location.accuracy.toDouble(),
                )
            )
        }
        .addOnFailureListener {
            if (continuation.isActive) continuation.resume(null)
        }
}

private fun mapAttendanceError(error: Throwable): String {
    val detail = if (error is HttpException) {
        parseErrorDetail(error.response()?.errorBody()?.string())
    } else {
        null
    }
    return when (detail) {
        "outside_radius" -> "You are outside the allowed classroom radius. Move closer and retry."
        "invalid_code" -> "The attendance code is incorrect."
        "poor_gps_accuracy" -> "GPS accuracy is low. Move to open sky and retry."
        "attendance_locked_for_session" -> "Too many failed attempts. Attendance is locked for this session."
        "not_enrolled" -> "You are not enrolled for this subject."
        "session_expired_or_inactive" -> "This session is no longer active."
        "already_marked" -> "Attendance is already marked for this session."
        else -> error.message ?: "Attendance failed"
    }
}

private fun parseErrorDetail(raw: String?): String? {
    if (raw.isNullOrBlank()) return null
    return try {
        val json = JSONObject(raw)
        when (val detail = json.opt("detail")) {
            is String -> detail
            else -> null
        }
    } catch (_: Exception) {
        null
    }
}

private fun buildDeviceId(context: Context): String {
    return Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID) ?: "android-device"
}

@Composable
fun SmartAttendanceApp() {
    val scope = rememberCoroutineScope()
    var token by remember { mutableStateOf("") }
    var me by remember { mutableStateOf<MeResponse?>(null) }
    var status by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }

    Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        BrandHeader()
        if (me == null) {
            LoginPanel(token = token, status = status, loading = loading, onTokenChange = { token = it }) {
                scope.launch {
                    loading = true
                    status = ""
                    try {
                        me = ApiClient.service.me("Bearer $token")
                    } catch (error: Exception) {
                        status = error.message ?: "Login failed"
                    } finally {
                        loading = false
                    }
                }
            }
        } else {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("${me!!.name} / ${me!!.role}", fontWeight = FontWeight.SemiBold)
                OutlinedButton(onClick = { me = null }) { Text("Sign out") }
            }
            if (!me!!.first_login_verified) {
                FirstLoginVerificationPanel(token = token, email = me!!.email, onVerified = {
                    scope.launch { me = ApiClient.service.me("Bearer $token") }
                })
            } else if (me!!.role == "student") {
                StudentDashboard(token = token)
            } else {
                FacultyDashboard(token = token)
            }
        }
    }
}

@Composable
fun BrandHeader() {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Surface(
            border = BorderStroke(2.dp, Color.Black),
            color = Color.Transparent,
            shape = MaterialTheme.shapes.extraLarge,
            modifier = Modifier.padding(top = 2.dp),
        ) {
            Text("SA", modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp), fontWeight = FontWeight.Black)
        }
        Column {
            Text("Smart Attendance", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
            Text("Enrollment-first attendance", color = Color(0xFF666666))
        }
    }
}

@Composable
fun LoginPanel(
    token: String,
    status: String,
    loading: Boolean,
    onTokenChange: (String) -> Unit,
    onLogin: () -> Unit,
) {
    ThinCard {
        Text("Clerk session", fontWeight = FontWeight.SemiBold)
        Text("Use the Clerk session token issued after college-mail login.", color = Color(0xFF666666))
        OutlinedTextField(
            value = token,
            onValueChange = onTokenChange,
            label = { Text("Session token") },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(onClick = onLogin, enabled = token.isNotBlank() && !loading) { Text(if (loading) "Checking" else "Continue") }
        if (status.isNotBlank()) Text(status, color = Color(0xFFB42318))
    }
}

@Composable
fun FirstLoginVerificationPanel(token: String, email: String, onVerified: () -> Unit) {
    val scope = rememberCoroutineScope()
    var otp by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("") }
    ThinCard {
        Text("Verify first login", fontWeight = FontWeight.SemiBold)
        Text("The initial password is shared only for onboarding. Verify the OTP sent to $email before continuing.", color = Color(0xFF666666))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = {
                scope.launch {
                    try {
                        val response = ApiClient.service.startFirstLoginOtp("Bearer $token")
                        status = "OTP sent by ${response.delivery}. Expires in ${response.expires_in_minutes} minutes."
                    } catch (error: Exception) {
                        status = error.message ?: "Could not send OTP"
                    }
                }
            }) { Text("Send OTP") }
            OutlinedTextField(value = otp, onValueChange = { otp = it.take(6) }, label = { Text("OTP") })
        }
        Button(enabled = otp.length == 6, onClick = {
            scope.launch {
                try {
                    ApiClient.service.verifyFirstLoginOtp("Bearer $token", FirstLoginOtpVerifyRequest(otp))
                    status = "Verified. Change your password in account settings."
                    onVerified()
                } catch (error: Exception) {
                    status = error.message ?: "OTP verification failed"
                }
            }
        }) { Text("Verify") }
        if (status.isNotBlank()) Text(status)
    }
}

@Composable
fun StudentDashboard(token: String) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var subjects by remember { mutableStateOf<List<SubjectOfferingDto>>(emptyList()) }
    var sessions by remember { mutableStateOf<List<ActiveSessionDto>>(emptyList()) }
    var summaries by remember { mutableStateOf<List<AttendanceSummaryDto>>(emptyList()) }
    var alerts by remember { mutableStateOf<List<AttendanceAlertDto>>(emptyList()) }
    var code by remember { mutableStateOf("") }
    var selectedSessionId by remember { mutableStateOf<Int?>(null) }
    var status by remember { mutableStateOf("") }
    var submitting by remember { mutableStateOf(false) }
    var locationPermissionGranted by remember { mutableStateOf(hasLocationPermission(context)) }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
    ) { granted ->
        locationPermissionGranted = granted
        if (!granted) {
            status = "Location permission denied. Enable location permission to mark attendance."
        }
    }

    LaunchedEffect(sessions) {
        if (sessions.none { it.id == selectedSessionId }) {
            selectedSessionId = sessions.firstOrNull()?.id
        }
    }

    fun refresh() {
        scope.launch {
            try {
                subjects = ApiClient.service.studentSubjects("Bearer $token")
                sessions = ApiClient.service.activeSessions("Bearer $token")
                summaries = ApiClient.service.attendanceSummary("Bearer $token")
                alerts = ApiClient.service.alerts("Bearer $token")
                status = ""
            } catch (error: Exception) {
                status = error.message ?: "Could not load student dashboard"
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = { refresh() }) { Text("Refresh") }
            OutlinedButton(onClick = {
                scope.launch {
                    try {
                        ApiClient.service.createLeaveRequest(
                            "Bearer $token",
                            CreateLeaveRequest("medical", "2026-05-10", "2026-05-10", "Medical leave request"),
                        )
                        status = "Leave request submitted"
                    } catch (error: Exception) {
                        status = error.message ?: "Leave request failed"
                    }
                }
            }) { Text("Request Leave") }
        }
        if (alerts.isNotEmpty()) {
            ThinCard {
                Text("Attendance alerts", fontWeight = FontWeight.SemiBold)
                alerts.forEach { Text("${it.subject_code}: ${it.percentage}% / ${it.level}") }
            }
        }
        ThinCard {
            Text("Active sessions", fontWeight = FontWeight.SemiBold)
            if (sessions.isEmpty()) {
                Text("No active sessions. Tap refresh.", color = Color(0xFF666666))
            } else {
                sessions.forEach { session ->
                    val selected = selectedSessionId == session.id
                    OutlinedButton(onClick = { selectedSessionId = session.id }) {
                        val marker = if (selected) "[Selected] " else ""
                        Text("${marker}#${session.id} ${session.subject_code} / ${session.session_type} / ${session.radius_meters}m")
                    }
                }
            }
            OutlinedTextField(value = code, onValueChange = { code = it.take(4) }, label = { Text("4-digit code") })
            Button(onClick = {
                if (!locationPermissionGranted) {
                    locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
                    return@Button
                }
                if (!isLocationEnabled(context)) {
                    status = "Location is turned off. Enable GPS/location services and retry."
                    return@Button
                }
                val sessionId = selectedSessionId
                if (sessionId == null) {
                    status = "Select an active session first."
                    return@Button
                }
                if (code.length != 4) {
                    status = "Enter the 4-digit attendance code."
                    return@Button
                }
                scope.launch {
                    try {
                        submitting = true
                        status = "Fetching your current location..."
                        val location = fetchCurrentLocation(context)
                        if (location == null) {
                            status = "Could not get accurate location. Move to open sky and retry."
                            return@launch
                        }
                        val response = ApiClient.service.markAttendance(
                            "Bearer $token",
                            in.bmsit.smartattendance.network.MarkAttendanceRequest(
                                sessionId,
                                code,
                                location.latitude,
                                location.longitude,
                                location.accuracyMeters,
                                buildDeviceId(context),
                            ),
                        )
                        status = "Marked ${response.status} at ${response.distance_from_teacher}m"
                        refresh()
                    } catch (error: Exception) {
                        status = mapAttendanceError(error)
                    } finally {
                        submitting = false
                    }
                }
            }, enabled = !submitting) { Text(if (submitting) "Marking..." else "Mark Attendance") }
        }
        DashboardList("My enrolled subjects", subjects.map { "${it.subject_code} / ${it.subject_name} / ${it.faculty_name}" })
        DashboardList("Attendance summary", summaries.map { "${it.subject_code}: ${it.present_sessions}/${it.total_sessions} (${it.percentage}%)" })
        if (status.isNotBlank()) Text(status, color = Color(0xFF111111))
    }
}

@Composable
fun FacultyDashboard(token: String) {
    val scope = rememberCoroutineScope()
    var offerings by remember { mutableStateOf<List<SubjectOfferingDto>>(emptyList()) }
    var report by remember { mutableStateOf<List<AttendanceSummaryDto>>(emptyList()) }
    var offeringId by remember { mutableStateOf("") }
    var lastSession by remember { mutableStateOf<StartSessionResponse?>(null) }
    var status by remember { mutableStateOf("") }
    fun refresh() {
        scope.launch {
            try {
                offerings = ApiClient.service.facultyOfferings("Bearer $token")
                report = ApiClient.service.facultyReport("Bearer $token")
                status = ""
            } catch (error: Exception) {
                status = error.message ?: "Could not load faculty dashboard"
            }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Button(onClick = { refresh() }) { Text("Refresh") }
        ThinCard {
            Text("Start session", fontWeight = FontWeight.SemiBold)
            OutlinedTextField(value = offeringId, onValueChange = { offeringId = it }, label = { Text("Offering ID") })
            Button(onClick = {
                scope.launch {
                    try {
                        lastSession = ApiClient.service.startSession(
                            "Bearer $token",
                            StartSessionRequest(offeringId.toInt(), "lecture", 12.9716, 77.5946, 10, 5),
                        )
                        status = "Code ${lastSession!!.code} created for session #${lastSession!!.id}"
                    } catch (error: Exception) {
                        status = error.message ?: "Could not start session"
                    }
                }
            }) { Text("Start Lecture") }
            lastSession?.let {
                Text("Session #${it.id}")
                Text("Code ${it.code}", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                OutlinedButton(onClick = {
                    scope.launch {
                        ApiClient.service.endSession("Bearer $token", it.id)
                        status = "Session ended"
                    }
                }) { Text("End Session") }
            }
        }
        DashboardList("Assigned offerings", offerings.map { "#${it.id} ${it.subject_code} / ${it.subject_name} / ${it.section}" })
        DashboardList("Attendance report", report.map { "${it.subject_code}: ${it.present_sessions} present across ${it.total_sessions} sessions (${it.percentage}%)" })
        if (status.isNotBlank()) Text(status)
    }
}

@Composable
fun DashboardList(title: String, rows: List<String>) {
    ThinCard {
        Text(title, fontWeight = FontWeight.SemiBold)
        if (rows.isEmpty()) {
            Text("No records yet.", color = Color(0xFF666666))
        } else {
            rows.forEach { row -> Text(row) }
        }
    }
}

@Composable
fun ThinCard(content: @Composable ColumnScope.() -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = BorderStroke(1.dp, Color(0xFFD8D8D2)),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            content()
        }
    }
}
