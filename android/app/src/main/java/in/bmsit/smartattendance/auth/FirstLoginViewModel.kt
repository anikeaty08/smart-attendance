package `in`.bmsit.smartattendance.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import `in`.bmsit.smartattendance.network.ApiClient
import `in`.bmsit.smartattendance.network.ApiErrorMapper
import `in`.bmsit.smartattendance.network.FirstLoginOtpVerifyRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class FirstLoginUiState(val otpInput: String = "", val status: String = "", val sending: Boolean = false, val verifying: Boolean = false)

/** Staff/faculty first-login OTP flow (students skip this on backend). */
class FirstLoginViewModel(private val bearerToken: String) : ViewModel() {
    private val _state = MutableStateFlow(FirstLoginUiState())
    val state: StateFlow<FirstLoginUiState> = _state.asStateFlow()

    fun onOtpChange(value: String) {
        _state.value = _state.value.copy(otpInput = value.take(6))
    }

    fun sendOtp() {
        viewModelScope.launch {
            _state.value = _state.value.copy(sending = true, status = "")
            try {
                val response = ApiClient.service.startFirstLoginOtp("Bearer $bearerToken")
                _state.value = _state.value.copy(
                    sending = false,
                    status = "OTP sent via ${response.delivery}. Expires in ${response.expires_in_minutes} minutes.",
                )
            } catch (error: Exception) {
                _state.value = _state.value.copy(sending = false, status = ApiErrorMapper.map(error))
            }
        }
    }

    fun verify(onSuccess: () -> Unit) {
        val otp = _state.value.otpInput
        if (otp.length != 6) return
        viewModelScope.launch {
            _state.value = _state.value.copy(verifying = true, status = "")
            try {
                ApiClient.service.verifyFirstLoginOtp("Bearer $bearerToken", FirstLoginOtpVerifyRequest(otp))
                _state.value = _state.value.copy(verifying = false, status = "Verified.")
                onSuccess()
            } catch (error: Exception) {
                _state.value = _state.value.copy(verifying = false, status = ApiErrorMapper.map(error))
            }
        }
    }

    class Factory(private val bearerToken: String) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = FirstLoginViewModel(bearerToken) as T
    }
}
