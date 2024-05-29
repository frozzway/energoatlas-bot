from energoatlas.models.background import DeviceWithLogs, TelegramMessageParams
from energoatlas.models.aiogram import Parameter


class MessageFormatter:
    @staticmethod
    def notification_message(device_logs: list[DeviceWithLogs]) -> TelegramMessageParams:
        items = []
        for device in device_logs:
            device_name = MessageFormatter.escape_markdown(device.device.name)
            object_name = MessageFormatter.escape_markdown(device.device.object_name)
            object_address = MessageFormatter.escape_markdown(device.device.object_address)
            header = (f'На устройстве: *{device_name}*, установленном на объекте *{object_name}* '
                      f'по адресу *{object_address}* обнаружены следующие срабатывания:\n\n')
            messages = [(f'{MessageFormatter.escape_markdown(log.latch_message)}\n'
                         f'{MessageFormatter.escape_markdown(log.latch_dt.strftime("%Y-%m-%d %H:%M:%S"))}') for log in device.logs]
            body = '\n\n'.join(messages)
            items.append(header + body)
        return TelegramMessageParams(text="\n\n".join(items), parse_mode='MarkdownV2')

    @staticmethod
    def device_params_message(device_name: str, device_params: list[Parameter]) -> TelegramMessageParams:
        text = f'__*{MessageFormatter.escape_markdown(device_name)}*__'
        for param in device_params:
            if param.measurement == 'bool':
                param_text = f'\n{param.descr}: {"Да" if param.val == 1 else "Нет"}'
            elif param.measurement in ['int', 'float']:
                param_text = f'\n{param.descr}: {param.val}'
            else:
                param_text = f'\n{param.descr}: {param.val} {param.measurement}'
            text += MessageFormatter.escape_markdown(param_text)
        return TelegramMessageParams(text=text, parse_mode='MarkdownV2')

    @staticmethod
    def escape_markdown(text: str) -> str:
        escaped_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in escaped_chars:
            text = text.replace(char, '\\' + char)
        return text
