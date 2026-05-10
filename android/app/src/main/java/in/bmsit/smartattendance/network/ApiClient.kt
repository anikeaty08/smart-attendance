package `in`.bmsit.smartattendance.network

import `in`.bmsit.smartattendance.config.AppConfig
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    val service: SmartAttendanceApi by lazy {
        Retrofit.Builder()
            .baseUrl(AppConfig.apiBaseUrl)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SmartAttendanceApi::class.java)
    }
}
