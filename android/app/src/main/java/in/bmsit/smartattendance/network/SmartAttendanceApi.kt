package in.bmsit.smartattendance.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface SmartAttendanceApi {
    @POST("/auth/google")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @GET("/student/subjects")
    suspend fun studentSubjects(@Header("Authorization") bearerToken: String): List<SubjectOfferingDto>

    @GET("/student/active-sessions")
    suspend fun activeSessions(@Header("Authorization") bearerToken: String): List<ActiveSessionDto>

    @POST("/student/attendance/mark")
    suspend fun markAttendance(
        @Header("Authorization") bearerToken: String,
        @Body request: MarkAttendanceRequest,
    ): MarkAttendanceResponse

    @GET("/faculty/offerings")
    suspend fun facultyOfferings(@Header("Authorization") bearerToken: String): List<SubjectOfferingDto>

    @POST("/faculty/sessions/start")
    suspend fun startSession(
        @Header("Authorization") bearerToken: String,
        @Body request: StartSessionRequest,
    ): StartSessionResponse
}

data class LoginRequest(val email: String)
data class TokenResponse(val access_token: String, val token_type: String, val role: String, val email: String, val name: String)
data class SubjectOfferingDto(
    val id: Int,
    val subject_code: String,
    val subject_name: String,
    val faculty_name: String,
    val academic_year: String,
    val semester_type: String,
    val section: String,
    val semester: Int,
    val enrollment_type: String?,
)
data class ActiveSessionDto(
    val id: Int,
    val subject_offering_id: Int,
    val subject_code: String,
    val subject_name: String,
    val faculty_name: String,
    val session_type: String,
    val starts_at: String,
    val ends_at: String,
    val radius_meters: Int,
)
data class MarkAttendanceRequest(
    val session_id: Int,
    val entered_code: String,
    val student_latitude: Double,
    val student_longitude: Double,
    val gps_accuracy_meters: Double,
    val device_id: String?,
)
data class MarkAttendanceResponse(val status: String, val distance_from_teacher: Double, val marked_at: String)
data class StartSessionRequest(
    val subject_offering_id: Int,
    val session_type: String,
    val teacher_latitude: Double,
    val teacher_longitude: Double,
    val radius_meters: Int,
    val duration_minutes: Int,
)
data class StartSessionResponse(val id: Int, val code: String, val starts_at: String, val ends_at: String, val radius_meters: Int)

