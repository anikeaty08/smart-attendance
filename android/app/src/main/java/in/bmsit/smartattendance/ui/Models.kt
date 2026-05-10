package `in`.bmsit.smartattendance.ui

data class StudentSubject(
    val subjectCode: String,
    val subjectName: String,
    val facultyName: String,
    val attendancePercent: Double,
)

data class ActiveSession(
    val id: Int,
    val subjectCode: String,
    val subjectName: String,
    val facultyName: String,
    val sessionType: String,
    val endsIn: String,
)

data class FacultyOffering(
    val id: Int,
    val subjectCode: String,
    val subjectName: String,
    val section: String,
)

