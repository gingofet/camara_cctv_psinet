package cl.cctvflow.camera.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import cl.cctvflow.camera.ui.screens.CameraScreen
import cl.cctvflow.camera.ui.screens.SelectionScreen
import cl.cctvflow.camera.ui.theme.CCTVFlowTheme

@Composable
fun CCTVFlowApp(viewModel: CCTVFlowViewModel) {
    val state by viewModel.uiState

    CCTVFlowTheme {
        when (state.screen) {
            AppScreen.SELECTION -> SelectionScreen(
                state = state,
                onDivisionSelected = viewModel::selectDivision,
                onTurnoSelected = viewModel::selectTurno,
                onSectorSelected = viewModel::selectSector,
                onCameraSelected = viewModel::selectCamera,
                onSearchChanged = viewModel::updateSearch,
                onContinue = viewModel::openCamera,
            )

            AppScreen.CAMERA -> CameraScreen(
                state = state,
                onBack = viewModel::backToSelection,
                onPrepareCapture = viewModel::prepareCapture,
                onCaptureSucceeded = viewModel::captureSucceeded,
                onCaptureFailed = viewModel::captureFailed,
                onDismissError = viewModel::clearError,
            )
        }
    }
}
