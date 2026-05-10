package `in`.bmsit.smartattendance.location

import org.junit.Assert.assertEquals
import org.junit.Test

class LocationRepositoryTest {
    private val repo = LocationRepository()

    @Test
    fun rejectsWhenProvidersDisabled() {
        assertEquals(LocationValidation.DISABLED, repo.validateLocationState(enabled = false, location = null))
    }

    @Test
    fun rejectsUnavailableFix() {
        assertEquals(LocationValidation.UNAVAILABLE, repo.validateLocationState(enabled = true, location = null))
    }

    @Test
    fun acceptsAccurateFix() {
        assertEquals(LocationValidation.OK, repo.validateLocationState(enabled = true, location = DeviceLocation(1.2, 3.4, 10.0)))
    }

    @Test
    fun rejectsPoorAccuracyPastThreshold() {
        assertEquals(
            LocationValidation.TOO_INACCURATE,
            repo.validateLocationState(enabled = true, location = DeviceLocation(1.0, 1.0, 75.0), maxAccuracyMeters = 50.0),
        )
    }
}
