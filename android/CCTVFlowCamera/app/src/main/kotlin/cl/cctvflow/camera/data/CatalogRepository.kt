package cl.cctvflow.camera.data

import android.content.Context
import cl.cctvflow.camera.domain.Division
import cl.cctvflow.camera.domain.Sector
import org.json.JSONObject

class CatalogRepository(
    private val context: Context,
) {
    fun load(division: Division): List<Sector> {
        val json = context.assets
            .open(division.assetName)
            .bufferedReader()
            .use { it.readText() }

        val root = JSONObject(json)
        return root.keys().asSequence().map { sectorName ->
            val cameraArray = root.getJSONArray(sectorName)
            val cameras = buildList {
                repeat(cameraArray.length()) { index ->
                    add(cameraArray.getString(index))
                }
            }

            Sector(
                name = sectorName,
                cameras = cameras,
            )
        }.toList()
    }
}

