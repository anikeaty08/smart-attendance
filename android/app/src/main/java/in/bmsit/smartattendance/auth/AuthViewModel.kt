package `in`.bmsit.smartattendance.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.bmsit.smartattendance.network.ApiClient
import `in`.bmsit.smartattendance.network.ApiErrorMapper
import `in`.bmsit.smartattendance.network.MeResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AuthUiState(
    val loading: Boolean = false,
    val tokenInput: String = "",
    val user: MeResponse? = null,
    val status: String = "",
)

class AuthViewModel(
    private val sessionStore: SessionStore,
) : ViewModel() {
    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        restoreSession()
    }

    fun onTokenChanged(value: String) {
        _uiState.value = _uiState.value.copy(tokenInput = value)
    }

    /** Deep link: `smartattendance://auth?session_token=...` */
    fun applyIncomingSessionToken(raw: String) {
        val trimmed = raw.trim()
        if (trimmed.isBlank()) return
        _uiState.value = _uiState.value.copy(tokenInput = trimmed)
        login()
    }

    fun restoreSession() {
        val stored = sessionStore.token()
        if (stored.isBlank()) return
        _uiState.value = _uiState.value.copy(tokenInput = stored)
        login()
    }

    fun login() {
        val token = _uiState.value.tokenInput.trim()
        if (token.isBlank()) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, status = "")
            try {
                val user = ApiClient.service.me("Bearer $token")
                sessionStore.saveToken(token)
                _uiState.value = _uiState.value.copy(user = user, status = "")
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(status = ApiErrorMapper.map(error))
            } finally {
                _uiState.value = _uiState.value.copy(loading = false)
            }
        }
    }

    fun refreshMe() {
        if (_uiState.value.tokenInput.isBlank()) return
        viewModelScope.launch {
            try {
                val user = ApiClient.service.me("Bearer ${_uiState.value.tokenInput}")
                _uiState.value = _uiState.value.copy(user = user)
            } catch (error: Exception) {
                _uiState.value = _uiState.value.copy(status = ApiErrorMapper.map(error))
            }
        }
    }

    fun logout() {
        sessionStore.clear()
        _uiState.value = AuthUiState()
    }

    class Factory(private val sessionStore: SessionStore) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = AuthViewModel(sessionStore) as T
    }
}
