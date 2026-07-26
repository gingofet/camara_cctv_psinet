package cl.cctvflow.camera.ui.screens

import android.Manifest
import android.content.ContentValues
import android.content.pm.PackageManager
import android.provider.MediaStore
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import cl.cctvflow.camera.camera.CameraPreview
import cl.cctvflow.camera.domain.CaptureRequest
import cl.cctvflow.camera.ui.CCTVFlowUiState

@Composable
fun CameraScreen(
    state: CCTVFlowUiState,
    onBack: () -> Unit,
    onPrepareCapture: () -> CaptureRequest?,
    onCaptureSucceeded: (CaptureRequest) -> Unit,
    onCaptureFailed: (String) -> Unit,
    onDismissError: () -> Unit,
) {
    val context = LocalContext.current
    var permissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.CAMERA,
            ) == PackageManager.PERMISSION_GRANTED,
        )
    }
    var imageCapture by remember { mutableStateOf<ImageCapture?>(null) }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        permissionGranted = granted
        if (!granted) {
            onCaptureFailed("Se necesita permiso de cámara para tomar fotografías.")
        }
    }

    Scaffold { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            if (permissionGranted) {
                CameraPreview(
                    modifier = Modifier.fillMaxSize(),
                    onImageCaptureReady = { imageCapture = it },
                    onCameraError = onCaptureFailed,
                )
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("CCTVFlow necesita permiso para usar la cámara.")
                    Button(onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) }) {
                        Text("Conceder permiso")
                    }
                }
            }

            Column(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.88f))
                    .padding(16.dp),
            ) {
                Text(
                    text = state.selectedCamera.orEmpty(),
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text = "${state.division.label} · ${state.turno.label} · ${state.selectedSector}",
                    style = MaterialTheme.typography.bodySmall,
                )
                state.lastSavedFile?.let {
                    Text(
                        text = "Última: $it",
                        color = MaterialTheme.colorScheme.primary,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            Row(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.92f))
                    .padding(16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedButton(
                    onClick = onBack,
                    enabled = !state.isCapturing,
                ) {
                    Text("Volver")
                }
                Button(
                    onClick = {
                        val capture = imageCapture
                        val request = onPrepareCapture()
                        if (capture == null || request == null) {
                            if (capture == null) {
                                onCaptureFailed("La cámara todavía no está lista.")
                            }
                            return@Button
                        }

                        takePhoto(
                            imageCapture = capture,
                            request = request,
                            context = context,
                            onSuccess = { onCaptureSucceeded(request) },
                            onError = onCaptureFailed,
                        )
                    },
                    enabled = permissionGranted && imageCapture != null && !state.isCapturing,
                    modifier = Modifier.weight(1f),
                ) {
                    if (state.isCapturing) {
                        CircularProgressIndicator()
                    } else {
                        Text("Tomar foto · ${state.savedCount}")
                    }
                }
            }
        }
    }

    state.errorMessage?.let { message ->
        AlertDialog(
            onDismissRequest = onDismissError,
            title = { Text("CCTVFlow Camera") },
            text = { Text(message) },
            confirmButton = {
                TextButton(onClick = onDismissError) {
                    Text("Aceptar")
                }
            },
        )
    }
}

private fun takePhoto(
    imageCapture: ImageCapture,
    request: CaptureRequest,
    context: android.content.Context,
    onSuccess: () -> Unit,
    onError: (String) -> Unit,
) {
    val values = ContentValues().apply {
        put(MediaStore.Images.Media.DISPLAY_NAME, request.fileName)
        put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
        put(
            MediaStore.Images.Media.RELATIVE_PATH,
            "Pictures/CCTVFlow/${request.division.label}/Turno_${request.turno.name}",
        )
    }

    val outputOptions = ImageCapture.OutputFileOptions.Builder(
        context.contentResolver,
        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
        values,
    ).build()

    imageCapture.takePicture(
        outputOptions,
        ContextCompat.getMainExecutor(context),
        object : ImageCapture.OnImageSavedCallback {
            override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                onSuccess()
            }

            override fun onError(exception: ImageCaptureException) {
                onError(
                    exception.message
                        ?: "No se pudo guardar la fotografía.",
                )
            }
        },
    )
}
