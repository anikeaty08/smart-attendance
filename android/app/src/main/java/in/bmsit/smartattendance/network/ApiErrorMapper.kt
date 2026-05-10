package `in`.bmsit.smartattendance.network

import com.google.gson.JsonParser
import retrofit2.HttpException

object ApiErrorMapper {
    fun map(error: Throwable): String {
        val detail = if (error is HttpException) {
            parseDetail(error.response()?.errorBody()?.string())
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
            "first_login_otp_locked" -> "Too many invalid OTP attempts. Contact admin."
            "first_login_otp_expired" -> "OTP has expired. Request a new one."
            "invalid_first_login_otp" -> "OTP is invalid. Try again."
            else -> error.message ?: "Request failed"
        }
    }

    fun parseDetail(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        return try {
            val obj = JsonParser.parseString(raw).asJsonObject
            val detail = obj.get("detail") ?: return null
            if (!detail.isJsonPrimitive || !detail.asJsonPrimitive.isString) return null
            detail.asString
        } catch (_: Exception) {
            null
        }
    }
}
