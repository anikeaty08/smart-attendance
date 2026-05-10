package `in`.bmsit.smartattendance.faculty

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.bmsit.smartattendance.network.ApiClient
import `in`.bmsit.smartattendance.network.ApiErrorMapper
import `in`.bmsit.smartattendance.network.AttendanceSummaryDto
import `in`.bmsit.smartattendance.network.StartSessionRequest
import `in`.bmsit.smartattendance.network.StartSessionResponse
import `in`.bmsit.smartattendance.network.SubjectOfferingDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class FacultyUiState(
    val offerings: List<SubjectOfferingDto> = emptyList(),
    val report: List<AttendanceSummaryDto> = emptyList(),
    val offeringIdInput: String = "",
    val lastSession: StartSessionResponse? = null,
    val status: String = "",
)

class FacultyViewModel(private val token: String) : ViewModel() {
    private val _uiState = MutableStateFlow(FacultyUiState())
    val uiState: StateFlow<FacultyUiState> = _uiState.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            try {
                val bearer = "Bearer $token"
                _uiState.value = _uiState.value.copy(
                    offerings = ApiClient.service.facultyOfferings(bearer),
                    report = ApiClient.service.facultyReport(bearer),
                    status = "",
                )
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(status = ApiErrorMapper.map(error))
            }
        }
    }

    fun onOfferingIdChanged(value: String) {
        _uiState.value = _uiState.value.copy(offeringIdInput = value)
    }

    fun startSession() {
        val offeringId = _uiState.value.offeringIdInput.toIntOrNull()
        if (offeringId == null) {
            _uiState.value = _uiState.value.copy(status = "Enter a valid offering ID.")
            return
        }
        viewModelScope.launch {
            try {
                val session = ApiClient.service.startSession(
                    "Bearer $token",
                    StartSessionRequest(offeringId, "lecture", 12.9716, 77.5946, 10, 5),
                )
                _uiState.value = _uiState.value.copy(lastSession = session, status = "Code ${session.code} created for session #${session.id}")
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(status = ApiErrorMapper.map(error))
            }
        }
    }

    fun endSession() {
        val sessionId = _uiState.value.lastSession?.id ?: return
        viewModelScope.launch {
            try {
                ApiClient.service.endSession("Bearer $token", sessionId)
                _uiState.value = _uiState.value.copy(lastSession = null, status = "Session ended")
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(status = ApiErrorMapper.map(error))
            }
        }
    }

    class Factory(private val token: String) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = FacultyViewModel(token) as T
    }
}
