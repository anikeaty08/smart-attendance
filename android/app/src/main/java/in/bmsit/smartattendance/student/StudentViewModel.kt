package `in`.bmsit.smartattendance.student

import android.content.Context
import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.bmsit.smartattendance.location.DeviceLocation
import `in`.bmsit.smartattendance.location.LocationRepository
import `in`.bmsit.smartattendance.location.LocationValidation
import `in`.bmsit.smartattendance.network.ActiveSessionDto
import `in`.bmsit.smartattendance.network.ApiClient
import `in`.bmsit.smartattendance.network.ApiErrorMapper
import `in`.bmsit.smartattendance.network.AttendanceAlertDto
import `in`.bmsit.smartattendance.network.AttendanceSummaryDto
import `in`.bmsit.smartattendance.network.CreateLeaveRequest
import `in`.bmsit.smartattendance.network.MarkAttendanceRequest
import `in`.bmsit.smartattendance.network.SubjectOfferingDto
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StudentUiState(
    val loading: Boolean = false,
    val submitting: Boolean = false,
    val subjects: List<SubjectOfferingDto> = emptyList(),
    val sessions: List<ActiveSessionDto> = emptyList(),
    val summaries: List<AttendanceSummaryDto> = emptyList(),
    val alerts: List<AttendanceAlertDto> = emptyList(),
    val selectedSessionId: Int? = null,
    val codeInput: String = "",
    val status: String = "",
)

class StudentViewModel(
    private val token: String,
    private val locationRepository: LocationRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(StudentUiState())
    val uiState: StateFlow<StudentUiState> = _uiState.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            try {
                val bearer = "Bearer $token"
                val subjects = ApiClient.service.studentSubjects(bearer)
                val sessions = ApiClient.service.activeSessions(bearer)
                val summaries = ApiClient.service.attendanceSummary(bearer)
                val alerts = ApiClient.service.alerts(bearer)
                val selected = _uiState.value.selectedSessionId?.takeIf { id -> sessions.any { it.id == id } } ?: sessions.firstOrNull()?.id
                _uiState.value = _uiState.value.copy(
                    loading = false,
                    subjects = subjects,
                    sessions = sessions,
                    summaries = summaries,
                    alerts = alerts,
                    selectedSessionId = selected,
                    status = "",
                )
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(loading = false, status = ApiErrorMapper.map(error))
            }
        }
    }

    fun selectSession(sessionId: Int) {
        _uiState.value = _uiState.value.copy(selectedSessionId = sessionId)
    }

    fun onCodeChanged(code: String) {
        _uiState.value = _uiState.value.copy(codeInput = code.take(4))
    }

    fun requestLeave() {
        viewModelScope.launch {
            try {
                ApiClient.service.createLeaveRequest(
                    "Bearer $token",
                    CreateLeaveRequest("medical", "2026-05-10", "2026-05-10", "Medical leave request"),
                )
                _uiState.value = _uiState.value.copy(status = "Leave request submitted")
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(status = ApiErrorMapper.map(error))
            }
        }
    }

    fun markAttendance(context: Context) {
        val sessionId = _uiState.value.selectedSessionId
        if (sessionId == null) {
            _uiState.value = _uiState.value.copy(status = "Select an active session first.")
            return
        }
        if (_uiState.value.codeInput.length != 4) {
            _uiState.value = _uiState.value.copy(status = "Enter the 4-digit attendance code.")
            return
        }
        if (!locationRepository.isLocationEnabled(context)) {
            _uiState.value = _uiState.value.copy(status = "Location is turned off. Enable GPS and retry.")
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(submitting = true, status = "Fetching your current location...")
            var location: DeviceLocation? = null
            repeat(2) { attempt ->
                location = locationRepository.fetchCurrentLocation(context)
                if (location != null) return@repeat
                if (attempt == 0) delay(650L)
            }
            var validation = locationRepository.validateLocationState(true, location)
            if (validation == LocationValidation.TOO_INACCURATE) {
                delay(800L)
                location = locationRepository.fetchCurrentLocation(context)
                validation = locationRepository.validateLocationState(true, location)
            }
            when (validation) {
                LocationValidation.DISABLED -> {
                    _uiState.value = _uiState.value.copy(submitting = false, status = "Location is turned off. Enable GPS and retry.")
                    return@launch
                }
                LocationValidation.UNAVAILABLE -> {
                    _uiState.value = _uiState.value.copy(submitting = false, status = "Could not get location. Move to open sky and retry.")
                    return@launch
                }
                LocationValidation.TOO_INACCURATE -> {
                    _uiState.value = _uiState.value.copy(submitting = false, status = "GPS accuracy is low. Wait for a stronger fix and retry.")
                    return@launch
                }
                LocationValidation.OK -> Unit
            }
            val fix = location!!
            try {
                val response = ApiClient.service.markAttendance(
                    "Bearer $token",
                    MarkAttendanceRequest(
                        session_id = sessionId,
                        entered_code = _uiState.value.codeInput,
                        student_latitude = fix.latitude,
                        student_longitude = fix.longitude,
                        gps_accuracy_meters = fix.accuracyMeters,
                        device_id = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID),
                    ),
                )
                _uiState.value = _uiState.value.copy(submitting = false, status = "Marked ${response.status} at ${response.distance_from_teacher}m")
                refresh()
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(submitting = false, status = ApiErrorMapper.map(error))
            }
        }
    }

    class Factory(private val token: String, private val locationRepository: LocationRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = StudentViewModel(token, locationRepository) as T
    }
}
