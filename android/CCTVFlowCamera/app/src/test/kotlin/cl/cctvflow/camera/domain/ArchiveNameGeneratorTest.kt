package cl.cctvflow.camera.domain

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Test

class ArchiveNameGeneratorTest {
    @Test
    fun `genera nombre identificable para el lote`() {
        val result = ArchiveNameGenerator.generate(
            division = Division.DRT,
            turno = Turno.B,
            createdAt = LocalDateTime.of(2026, 7, 27, 1, 30, 45),
        )

        assertEquals(
            "CCTVFlow_DRT_Turno_B_20260727_013045.zip",
            result,
        )
    }
}
