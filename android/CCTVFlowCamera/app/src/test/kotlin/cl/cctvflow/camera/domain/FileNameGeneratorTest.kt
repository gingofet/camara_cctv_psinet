package cl.cctvflow.camera.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class FileNameGeneratorTest {
    @Test
    fun generatesExpectedCctvFlowName() {
        assertEquals(
            "20740_Cruce_Rampa_4_0001.jpg",
            FileNameGenerator.generate("20740 Cruce Rampa 4", 1),
        )
    }

    @Test
    fun removesAccentsAndKeepsCameraCodeSeparator() {
        assertEquals(
            "RTSULFP001-Bahia_Lado_Mina_0012.jpg",
            FileNameGenerator.generate("RTSULFP001-Bahía Lado Mina", 12),
        )
    }
}

