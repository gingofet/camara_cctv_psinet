package cl.cctvflow.camera.ui

import android.content.ClipData
import android.content.Intent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.platform.LocalContext
import cl.cctvflow.camera.ui.screens.CameraScreen
import cl.cctvflow.camera.ui.screens.SelectionScreen
import cl.cctvflow.camera.ui.theme.CCTVFlowTheme

@Composable
fun CCTVFlowApp(viewModel: CCTVFlowViewModel) {
    val state by viewModel.uiState
    val context = LocalContext.current

    LaunchedEffect(state.archiveReady) {
        state.archiveReady?.let { archive ->
            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "application/zip"
                putExtra(Intent.EXTRA_STREAM, archive.uri)
                clipData = ClipData.newUri(
                    context.contentResolver,
                    archive.fileName,
                    archive.uri,
                )
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            context.startActivity(
                Intent.createChooser(
                    shareIntent,
                    "Compartir ${archive.fileName}",
                ),
            )
            viewModel.archiveShared()
        }
    }

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
                onExportPhotos = viewModel::exportPhotos,
                onDismissError = viewModel::clearError,
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
