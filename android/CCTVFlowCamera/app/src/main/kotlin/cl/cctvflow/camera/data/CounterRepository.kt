package cl.cctvflow.camera.data

import android.content.Context
import cl.cctvflow.camera.domain.Division
import cl.cctvflow.camera.domain.FileNameGenerator

class CounterRepository(context: Context) {
    private val preferences = context.getSharedPreferences(
        "cctvflow_photo_counters",
        Context.MODE_PRIVATE,
    )

    fun next(division: Division, cameraName: String): Int {
        val key = FileNameGenerator.counterKey(division, cameraName)
        return preferences.getInt(key, 0) + 1
    }

    fun confirm(
        division: Division,
        cameraName: String,
        sequence: Int,
    ) {
        val key = FileNameGenerator.counterKey(division, cameraName)
        val current = preferences.getInt(key, 0)
        if (sequence > current) {
            preferences.edit().putInt(key, sequence).apply()
        }
    }
}

