from energoatlas.models.background import DeviceWithLogs, TelegramMessageParams


class MessageFormatter:
    @staticmethod
    def notification_message(device_logs: list[DeviceWithLogs]) -> TelegramMessageParams:
        items = []
        for device in device_logs:
            header = (f'На устройстве: *{device.device.name}*, установленном на объекте *{device.device.object_name}* '
                      f'по адресу *{device.device.object_address}* обнаружены следующие срабатывания:\n\n')
            messages = [f'{log.latch_message}\n{log.latch_dt.strftime("%Y-%m-%d %H:%M:%S")}' for log in device.logs]
            body = '\n\n'.join(messages)
            items.append(header + body)
        return TelegramMessageParams(text=MessageFormatter.escape_markdown("\n\n".join(items)), parse_mode='MarkdownV2')

    @staticmethod
    def escape_markdown(text: str) -> str:
        return text.replace('-', '\\-').replace('(', '\\(').replace(')', '\\)')
