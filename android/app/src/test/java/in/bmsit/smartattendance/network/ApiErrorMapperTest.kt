package `in`.bmsit.smartattendance.network

import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

class ApiErrorMapperTest {
    @Test
    fun parseDetailReadsStringCodes() {
        assertEquals("invalid_code", ApiErrorMapper.parseDetail("{\"detail\":\"invalid_code\"}"))
    }

    @Test
    fun mapTranslatesAttendanceDetailFromHttp() {
        val body = "{\"detail\":\"outside_radius\"}"
            .toResponseBody("application/json".toMediaTypeOrNull())
        val retrofitResponse = Response.error<Any>(400, body)
        val mapped = ApiErrorMapper.map(HttpException(retrofitResponse))
        assertTrue(mapped.contains("outside", ignoreCase = true))
    }

    @Test
    fun mapFallsBackToMessageForPlainErrors() {
        val mapped = ApiErrorMapper.map(RuntimeException("network down"))
        assertEquals("network down", mapped)
    }
}
