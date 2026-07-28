package cl.cctvflow.camera.domain

import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

object ArchiveNameGenerator {
    private val formatter = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss")

    fun generate(
        division: Division,
        turno: Turno,
        createdAt: LocalDateTime = LocalDateTime.now(),
    ): String =
        "CCTVFlow_${division.label}_Turno_${turno.name}_${createdAt.format(formatter)}.zip"
}
