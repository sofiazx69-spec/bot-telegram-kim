import os
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configuração de Logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Chaves obtidas do Telegram e da API de Consulta (via variáveis de ambiente)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "COLE_SEU_TOKEN_TELEGRAM_AQUI")
APIBRASIL_TOKEN = os.environ.get("APIBRASIL_TOKEN", "COLE_SEU_TOKEN_APIBRASIL_AQUI")

# Endpoint de consulta da API
API_URL = "https://api.apibrasil.com.br/v2/dados/consulta"

# ID do Telegram dos funcionários autorizados (opcional)
USUARIOS_AUTORIZADOS = [] 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if USUARIOS_AUTORIZADOS and user_id not in USUARIOS_AUTORIZADOS:
        await update.message.reply_text(f"⛔ Acesso restrito. Seu ID do Telegram é: {user_id}")
        return

    mensagem_boas_vindas = (
        "🤖 **Bot de Inteligência Comercial — Kim**\n\n"
        "Envie o **CPF**, **Telefone** ou **Nome Completo** "
        "para realizar a consulta completa do cliente."
    )
    await update.message.reply_text(mensagem_boas_vindas, parse_mode="Markdown")

async def consultar_cliente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if USUARIOS_AUTORIZADOS and user_id not in USUARIOS_AUTORIZADOS:
        await update.message.reply_text("⛔ Você não tem permissão para usar este bot.")
        return

    termo = update.message.text.strip()
    await update.message.reply_text("🔎 Buscando ficha cadastral nas bases oficiais...")

    try:
        headers = {
            "Authorization": f"Bearer {APIBRASIL_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"query": termo}

        # Requisição à API de consulta
        response = requests.post(API_URL, json=payload, headers=headers, timeout=15)

        if response.status_code == 200:
            dados = response.json()
            
            # Tratamento de telefones (único ou lista)
            telefones_raw = dados.get("telefones", dados.get("telefone", "Não informado"))
            if isinstance(telefones_raw, list):
                telefones_str = "\n".join([f"  • {t}" for t in telefones_raw])
            else:
                telefones_str = f"  • {telefones_raw}"

            # Tratamento de filhos / dependentes
            filhos_raw = dados.get("filhos", dados.get("dependentes", "Nenhum informado"))
            if isinstance(filhos_raw, list):
                filhos_str = "\n".join([f"  • {f}" for f in filhos_raw])
            else:
                filhos_str = f"  • {filhos_raw}"

            # Tratamento de Endereço
            rua = dados.get("logradouro", dados.get("rua", ""))
            numero = dados.get("numero", "S/N")
            bairro = dados.get("bairro", "")
            cidade = dados.get("cidade", "")
            uf = dados.get("uf", "")
            cep = dados.get("cep", "")

            endereco_formatado = f"{rua}, {numero} - {bairro}, {cidade}/{uf} (CEP: {cep})".strip(" ,-")
            if not endereco_formatado or endereco_formatado == "- / (CEP: )":
                endereco_formatado = dados.get("endereco", "Não informado")

            # Montagem da resposta completa
            resposta = (
                f"✅ **Ficha Cadastral Encontrada**\n\n"
                f"👤 **Nome Completo:** {dados.get('nome', 'Não informado')}\n"
                f"📄 **CPF:** {dados.get('cpf', termo)}\n\n"
                
                f"👨‍👩‍👦 **Filiação:**\n"
                f"  • **Mãe:** {dados.get('nome_mae', dados.get('mae', 'Não informado'))}\n"
                f"  • **Pai:** {dados.get('nome_pai', dados.get('pai', 'Não informado'))}\n\n"
                
                f"👶 **Filhos / Dependentes:**\n{filhos_str}\n\n"
                
                f"📞 **Telefone(s):**\n{telefones_str}\n\n"
                
                f"🏠 **Endereço Completo:**\n{endereco_formatado}"
            )
        else:
            resposta = f"❌ Nenhum registro localizado para o termo enviado: `{termo}`."

    except Exception as e:
        logging.error(f"Erro na consulta: {e}")
        resposta = "⚠️ Ocorreu um erro ao consultar os servidores de dados. Tente novamente em instantes."

    await update.message.reply_text(resposta, parse_mode="Markdown")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), consultar_cliente))
    
    print("Bot da Kim rodando com sucesso...")
    app.run_polling()
