package cl.cctvflow.camera.data

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.provider.MediaStore
import cl.cctvflow.camera.domain.ArchiveNameGenerator
import cl.cctvflow.camera.domain.Division
import cl.cctvflow.camera.domain.Turno
import java.io.BufferedOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

data class PhotoArchive(
    val uri: Uri,
    val fileName: String,
    val photoCount: Int,
)

class PhotoArchiveRepository(context: Context) {
    private val resolver = context.applicationContext.contentResolver

    fun create(
        division: Division,
        turno: Turno,
    ): PhotoArchive {
        val photos = findPhotos(division, turno)
        check(photos.isNotEmpty()) {
            "No hay fotografías en ${division.label} · ${turno.label}."
        }

        val duplicateName = photos
            .groupingBy { it.displayName }
            .eachCount()
            .entries
            .firstOrNull { it.value > 1 }
            ?.key
        check(duplicateName == null) {
            "Hay fotografías repetidas con el nombre $duplicateName. " +
                "Corrige el duplicado antes de crear el ZIP."
        }

        val fileName = ArchiveNameGenerator.generate(division, turno)
        val archiveUri = createPendingArchive(fileName)

        try {
            resolver.openOutputStream(archiveUri, "w").use { output ->
                checkNotNull(output) { "Android no permitió escribir el archivo ZIP." }
                ZipOutputStream(BufferedOutputStream(output)).use { zip ->
                    photos.forEach { photo ->
                        zip.putNextEntry(ZipEntry(photo.displayName))
                        resolver.openInputStream(photo.uri).use { input ->
                            checkNotNull(input) {
                                "No se pudo leer ${photo.displayName}."
                            }
                            input.copyTo(zip)
                        }
                        zip.closeEntry()
                    }
                }
            }
            publishArchive(archiveUri)
        } catch (error: Exception) {
            resolver.delete(archiveUri, null, null)
            throw error
        }

        return PhotoArchive(
            uri = archiveUri,
            fileName = fileName,
            photoCount = photos.size,
        )
    }

    private fun findPhotos(
        division: Division,
        turno: Turno,
    ): List<PhotoRef> {
        val relativePath = "Pictures/CCTVFlow/${division.label}/Turno_${turno.name}/"
        val projection = arrayOf(
            MediaStore.Images.Media._ID,
            MediaStore.Images.Media.DISPLAY_NAME,
        )
        val selection =
            "${MediaStore.Images.Media.RELATIVE_PATH} = ? AND " +
                "${MediaStore.Images.Media.MIME_TYPE} = ?"
        val selectionArgs = arrayOf(relativePath, "image/jpeg")
        val sortOrder =
            "${MediaStore.Images.Media.DATE_ADDED} ASC, " +
                "${MediaStore.Images.Media._ID} ASC"

        return resolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
            projection,
            selection,
            selectionArgs,
            sortOrder,
        )?.use { cursor ->
            val idColumn = cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
            val nameColumn =
                cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME)
            buildList {
                while (cursor.moveToNext()) {
                    val id = cursor.getLong(idColumn)
                    val uri = Uri.withAppendedPath(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                        id.toString(),
                    )
                    add(
                        PhotoRef(
                            uri = uri,
                            displayName = cursor.getString(nameColumn),
                        ),
                    )
                }
            }
        }.orEmpty()
    }

    private fun createPendingArchive(fileName: String): Uri {
        val values = ContentValues().apply {
            put(MediaStore.Downloads.DISPLAY_NAME, fileName)
            put(MediaStore.Downloads.MIME_TYPE, "application/zip")
            put(MediaStore.Downloads.RELATIVE_PATH, "Download/CCTVFlow")
            put(MediaStore.Downloads.IS_PENDING, 1)
        }
        return checkNotNull(
            resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values),
        ) {
            "Android no pudo crear el archivo ZIP."
        }
    }

    private fun publishArchive(uri: Uri) {
        val values = ContentValues().apply {
            put(MediaStore.Downloads.IS_PENDING, 0)
        }
        check(resolver.update(uri, values, null, null) == 1) {
            "El ZIP se creó, pero Android no pudo publicarlo."
        }
    }

    private data class PhotoRef(
        val uri: Uri,
        val displayName: String,
    )
}
