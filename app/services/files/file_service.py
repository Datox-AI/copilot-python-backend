from uuid import uuid4


class FileUploaderService:
    def __init__(self, context, blob_storage_service):
        self._context = context
        self._blob_storage_service = blob_storage_service

    async def save_file(self, file_metadata, cancellation_token):
        file_id = uuid4()

        file = File(
            id=file_id,
            file_name=file_metadata.name,
            blob_name=f"{file_id}_{file_metadata.name}"
        )

        self._context.files.add(file)
        await self._blob_storage_service.store_file_async(file_metadata.content, file.blob_name, cancellation_token)
        await self._context.save_changes_async(cancellation_token)

        return file

    async def save_files(self, file_metadata, cancellation_token):
        files = []
        for file in file_metadata:
            files.append(await self.save_file(file, cancellation_token))
        return files

    async def get_files(self, files, chat_id, cancellation_token):
        result = []
        for file in files:
            file_stream = await self._blob_storage_service.get_file_async(file.blob_name, cancellation_token)
            result.append(FileMetadata(file_stream, file.file_name))
        return result

    async def delete_file(self, id, delete_blob, cancellation_token):
        file = await self._context.files.find_async(id, cancellation_token)
        if file is None:
            return

        self._context.files.remove(file)
        await self._context.save_changes_async(cancellation_token)

        if delete_blob:
            await self._blob_storage_service.delete_file_async(file.blob_name, cancellation_token)

    async def delete_files(self, ids, delete_blob, cancellation_token):
        for id in ids:
            await self.delete_file(id, True, cancellation_token)
