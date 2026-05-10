package `in`.bmsit.smartattendance.location

import android.annotation.SuppressLint
import android.content.Context
import android.location.LocationManager
import android.os.Build
import com.google.android.gms.location.CurrentLocationRequest
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

data class DeviceLocation(val latitude: Double, val longitude: Double, val accuracyMeters: Double)

enum class LocationValidation {
    OK,
    DISABLED,
    TOO_INACCURATE,
    UNAVAILABLE,
}

class LocationRepository {
    fun isLocationEnabled(context: Context): Boolean {
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as? LocationManager ?: return false
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            manager.isLocationEnabled
        } else {
            manager.isProviderEnabled(LocationManager.GPS_PROVIDER) ||
                manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
        }
    }

    @SuppressLint("MissingPermission")
    suspend fun fetchCurrentLocation(context: Context): DeviceLocation? = suspendCancellableCoroutine { continuation ->
        val locationClient = LocationServices.getFusedLocationProviderClient(context)
        val request = CurrentLocationRequest.Builder()
            .setDurationMillis(8000)
            .setMaxUpdateAgeMillis(3000)
            .build()
        locationClient
            .getCurrentLocation(request, null)
            .addOnSuccessListener { location ->
                if (!continuation.isActive) return@addOnSuccessListener
                if (location == null) {
                    continuation.resume(null)
                    return@addOnSuccessListener
                }
                continuation.resume(DeviceLocation(location.latitude, location.longitude, location.accuracy.toDouble()))
            }
            .addOnFailureListener {
                if (continuation.isActive) continuation.resume(null)
            }
    }

    fun validateLocationState(enabled: Boolean, location: DeviceLocation?, maxAccuracyMeters: Double = 50.0): LocationValidation {
        if (!enabled) return LocationValidation.DISABLED
        if (location == null) return LocationValidation.UNAVAILABLE
        if (location.accuracyMeters > maxAccuracyMeters) return LocationValidation.TOO_INACCURATE
        return LocationValidation.OK
    }
}
