package in.bmsit.smartattendance.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path

interface SmartAttendanceApi {
    @GET("/me")
    suspend fun me(@Header("Authorization") bearerToken: String): MeResponse

    @POST("/auth/first-login/start")
    suspend fun startFirstLoginOtp(@Header("Authorization") bearerToken: String): FirstLoginOtpStartResponse

    @POST("/auth/first-login/verify")
    suspend fun verifyFirstLoginOtp(
        @Header("Authorization") bearerToken: String,
        @Body request: FirstLoginOtpVerifyRequest,
    ): FirstLoginOtpVerifyResponse

    @GET("/student/subjects")
    suspend fun studentSubjects(@Header("Authorization") bearerToken: String): List<SubjectOfferingDto>

    @GET("/student/active-sessions")
    suspend fun activeSessions(@Header("Authorization") bearerToken: String): List<ActiveSessionDto>

    @POST("/student/attendance/mark")
    suspend fun markAttendance(
        @Header("Authorization") bearerToken: String,
        @Body request: MarkAttendanceRequest,
    ): MarkAttendanceResponse

    @GET("/student/attendance/summary")
    suspend fun attendanceSummary(@Header("Authorization") bearerToken: String): List<AttendanceSummaryDto>

    @GET("/student/alerts")
    suspend fun alerts(@Header("Authorization") bearerToken: String): List<AttendanceAlertDto>

    @GET("/student/leave-requests")
    suspend fun leaveRequests(@Header("Authorization") bearerToken: String): List<LeaveRequestDto>

    @POST("/student/leave-requests")
    suspend fun createLeaveRequest(
        @Header("Authorization") bearerToken: String,
        @Body request: CreateLeaveRequest,
    ): LeaveRequestDto

    @GET("/student/condonation-requests")
    suspend fun condonationRequests(@Header("Authorization") bearerToken: String): List<CondonationRequestDto>

    @POST("/student/condonation-requests")
    suspend fun createCondonationRequest(
        @Header("Authorization") bearerToken: String,
        @Body request: CreateCondonationRequest,
    ): CondonationRequestDto

    @GET("/faculty/offerings")
    suspend fun facultyOfferings(@Header("Authorization") bearerToken: String): List<SubjectOfferingDto>

    @POST("/faculty/sessions/start")
    suspend fun startSession(
        @Header("Authorization") bearerToken: String,
        @Body request: StartSessionRequest,
    ): StartSessionResponse

    @POST("/faculty/sessions/{sessionId}/end")
    suspend fun endSession(
        @Header("Authorization") bearerToken: String,
        @Path("sessionId") sessionId: Int,
    ): Map<String, Any>

    @GET("/faculty/sessions/{sessionId}/records")
    suspend fun sessionRecords(
        @Header("Authorization") bearerToken: String,
        @Path("sessionId") sessionId: Int,
    ): List<AttendanceRecordDto>

    @GET("/faculty/attendance/report")
    suspend fun facultyReport(@Header("Authorization") bearerToken: String): List<AttendanceSummaryDto>
}

data class MeResponse(
    val id: Int,
    val role: String,
    val email: String,
    val name: String,
    val is_admin: Boolean,
    val is_hod: Boolean,
    val department_id: Int?,
    val department_name: String?,
    val first_login_verified: Boolean,
    val must_change_password: Boolean,
)

data class FirstLoginOtpStartResponse(val status: String, val email: String, val expires_in_minutes: Int, val delivery: String)
data class FirstLoginOtpVerifyRequest(val otp: String)
data class FirstLoginOtpVerifyResponse(val status: String, val first_login_verified: Boolean)

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
data class AttendanceSummaryDto(
    val subject_offering_id: Int,
    val subject_code: String,
    val subject_name: String,
    val total_sessions: Int,
    val present_sessions: Int,
    val percentage: Double,
)
data class AttendanceAlertDto(val subject_code: String, val subject_name: String, val percentage: Double, val level: String)
data class AttendanceRecordDto(
    val id: Int,
    val student_id: Int,
    val student_name: String,
    val usn: String,
    val status: String,
    val distance_from_teacher: Double,
    val marked_at: String,
)
data class CreateLeaveRequest(
    val leave_type: String,
    val start_date: String,
    val end_date: String,
    val reason: String,
    val document_path: String? = null,
)
data class LeaveRequestDto(
    val id: Int,
    val leave_type: String,
    val start_date: String,
    val end_date: String,
    val reason: String,
    val status: String,
)
data class CreateCondonationRequest(val subject_offering_id: Int, val reason: String)
data class CondonationRequestDto(
    val id: Int,
    val subject_offering_id: Int,
    val subject_code: String,
    val subject_name: String,
    val current_percentage: Double,
    val reason: String,
    val status: String,
)
data class StartSessionRequest(
    val subject_offering_id: Int,
    val session_type: String,
    val teacher_latitude: Double,
    val teacher_longitude: Double,
    val radius_meters: Int,
    val duration_minutes: Int,
)
data class StartSessionResponse(val id: Int, val code: String, val starts_at: String, val ends_at: String, val radius_meters: Int)
