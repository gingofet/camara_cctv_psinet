package cl.cctvflow.camera.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import cl.cctvflow.camera.data.CatalogRepository
import cl.cctvflow.camera.data.CounterRepository
import cl.cctvflow.camera.domain.CaptureRequest
import cl.cctvflow.camera.domain.Division
import cl.cctvflow.camera.domain.FileNameGenerator
import cl.cctvflow.camera.domain.Sector
import cl.cctvflow.camera.domain.Turno
import java.text.Normalizer
import java.util.Locale

enum class AppScreen {
    SELECTION,
    CAMERA,
}

data class CCTVFlowUiState(
    val screen: AppScreen = AppScreen.SELECTION,
    val division: Division = Division.DRT,
    val turno: Turno = Turno.A,
    val sectors: List<Sector> = emptyList(),
    val selectedSector: String? = null,
    val selectedCamera: String? = null,
    val searchQuery: String = "",
    val isCapturing: Boolean = false,
    val savedCount: Int = 0,
    val lastSavedFile: String? = null,
    val errorMessage: String? = null,
) {
    val camerasInSelectedSector: List<String>
        get() = sectors
            .firstOrNull { it.name == selectedSector }
            ?.cameras
            .orEmpty()

    val filteredCameras: List<String>
        get() {
            val query = normalize(searchQuery)
            if (query.isBlank()) return camerasInSelectedSector
            return camerasInSelectedSector.filter { normalize(it).contains(query) }
        }

    val canOpenCamera: Boolean
        get() = selectedSector != null && selectedCamera != null

    companion object {
        private fun normalize(text: String): String = Normalizer
            .normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("\\p{M}+"), "")
            .replace(Regex("[^a-z0-9]+"), " ")
            .trim()
    }
}

class CCTVFlowViewModel(
    private val catalogRepository: CatalogRepository,
    private val counterRepository: CounterRepository,
) : ViewModel() {
    var uiState = androidx.compose.runtime.mutableStateOf(CCTVFlowUiState())
        private set

    init {
        loadDivision(Division.DRT)
    }

    fun selectDivision(division: Division) {
        if (division != uiState.value.division) {
            loadDivision(division)
        }
    }

    fun selectTurno(turno: Turno) {
        uiState.value = uiState.value.copy(turno = turno)
    }

    fun selectSector(sector: String) {
        uiState.value = uiState.value.copy(
            selectedSector = sector,
            selectedCamera = null,
            searchQuery = "",
        )
    }

    fun selectCamera(camera: String) {
        uiState.value = uiState.value.copy(selectedCamera = camera)
    }

    fun updateSearch(query: String) {
        uiState.value = uiState.value.copy(searchQuery = query)
    }

    fun openCamera() {
        if (uiState.value.canOpenCamera) {
            uiState.value = uiState.value.copy(
                screen = AppScreen.CAMERA,
                errorMessage = null,
            )
        }
    }

    fun backToSelection() {
        uiState.value = uiState.value.copy(
            screen = AppScreen.SELECTION,
            isCapturing = false,
            errorMessage = null,
        )
    }

    fun prepareCapture(): CaptureRequest? {
        val state = uiState.value
        val sector = state.selectedSector ?: return null
        val camera = state.selectedCamera ?: return null
        if (state.isCapturing) return null

        val sequence = counterRepository.next(state.division, camera)
        val request = CaptureRequest(
            division = state.division,
            turno = state.turno,
            sector = sector,
            camera = camera,
            sequence = sequence,
            fileName = FileNameGenerator.generate(camera, sequence),
        )

        uiState.value = state.copy(
            isCapturing = true,
            errorMessage = null,
        )
        return request
    }

    fun captureSucceeded(request: CaptureRequest) {
        counterRepository.confirm(
            division = request.division,
            cameraName = request.camera,
            sequence = request.sequence,
        )
        uiState.value = uiState.value.copy(
            isCapturing = false,
            savedCount = uiState.value.savedCount + 1,
            lastSavedFile = request.fileName,
            errorMessage = null,
        )
    }

    fun captureFailed(message: String) {
        uiState.value = uiState.value.copy(
            isCapturing = false,
            errorMessage = message,
        )
    }

    fun clearError() {
        uiState.value = uiState.value.copy(errorMessage = null)
    }

    private fun loadDivision(division: Division) {
        runCatching { catalogRepository.load(division) }
            .onSuccess { sectors ->
                uiState.value = CCTVFlowUiState(
                    division = division,
                    turno = uiState.value.turno,
                    sectors = sectors,
                )
            }
            .onFailure { error ->
                uiState.value = uiState.value.copy(
                    division = division,
                    sectors = emptyList(),
                    selectedSector = null,
                    selectedCamera = null,
                    errorMessage = "No se pudo cargar el catálogo: ${error.message}",
                )
            }
    }

    class Factory(
        private val catalogRepository: CatalogRepository,
        private val counterRepository: CounterRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            require(modelClass.isAssignableFrom(CCTVFlowViewModel::class.java))
            return CCTVFlowViewModel(
                catalogRepository = catalogRepository,
                counterRepository = counterRepository,
            ) as T
        }
    }
}

