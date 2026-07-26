package cl.cctvflow.camera.domain

import java.text.Normalizer
import java.util.Locale

object FileNameGenerator {
    fun generate(cameraName: String, sequence: Int): String {
        require(cameraName.isNotBlank()) { "El nombre de cámara no puede estar vacío." }
        require(sequence > 0) { "El correlativo debe ser mayor que cero." }

        val sanitizedName = Normalizer
            .normalize(cameraName.trim(), Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .replace(Regex("[^A-Za-z0-9-]+"), "_")
            .replace(Regex("_+"), "_")
            .trim('_')

        require(sanitizedName.isNotBlank()) {
            "El nombre de cámara no contiene caracteres válidos."
        }

        return String.format(
            Locale.ROOT,
            "%s_%04d.jpg",
            sanitizedName,
            sequence,
        )
    }

    fun counterKey(division: Division, cameraName: String): String {
        val normalizedCamera = Normalizer
            .normalize(cameraName.trim().lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .replace(Regex("[^a-z0-9]+"), "_")
            .trim('_')

        return "${division.name}_$normalizedCamera"
    }
}

