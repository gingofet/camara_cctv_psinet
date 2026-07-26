package cl.cctvflow.camera.domain

enum class Division(
    val label: String,
    val assetName: String,
) {
    DCH_SUBTE("DCH-SUBTE", "catalogos/sectores.json"),
    DRT("DRT", "catalogos/sectores_drt.json"),
}

enum class Turno(val label: String) {
    A("Turno A"),
    B("Turno B"),
}

data class Sector(
    val name: String,
    val cameras: List<String>,
)

data class CaptureRequest(
    val division: Division,
    val turno: Turno,
    val sector: String,
    val camera: String,
    val sequence: Int,
    val fileName: String,
)

