"""
    This script runs the main app for querying data. 

    Script adapted from https://github.com/jcheng5/py-sidebot/blob/main/app.py
"""
import traceback
from pathlib import Path
from typing import Annotated

import dotenv
import duckdb
import faicons as fa
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

dotenv.load_dotenv()

import query
from explain_plot import explain_plot
from shared import cells_df  # Load data and compute static values
from tool import Toolbox, tool

here = Path(__file__).parent

greeting = """
You can use this sidebar to filter and sort the data based on the columns available in the cell measurements table. Here are some examples of the kinds of questions you can ask me:

1. Filtering: "Show only the top 3 cell types that had the highest counts overall."
2. Sorting: "Show all data sorted by Name in descending order."
3. Answer questions about the data: "How do B cell counts compare between PD-L1 positive and negative groups?"

You can also say "Reset" to clear the current filter/sort, or "Help" for more usage tips.
"""

# Set to True to greatly enlarge chat UI (for presenting to a larger audience)
DEMO_MODE=False

icon_ellipsis = fa.icon_svg("ellipsis")
icon_explain = ui.img(src="stars.svg")

app_ui = ui.page_sidebar(
    ui.sidebar(
        # ui.input_text(
        #     "input_replicate_token",
        #     "Paste your Replicate API key here:"
        # ),
        ui.input_select(
            "model",
            "LLM used to query data",
            choices={
                "gpt-4o": "GPT-4o (OpenAI API required)",
                "replicate/meta/meta-llama-3-8b-instruct": "Llama3 (Replicate API required)",
            },
        ).add_class("mb-3"),
        ui.chat_ui("chat", height="100%", style = None if not DEMO_MODE else "zoom: 1.6;"),
        open="desktop",
        width=400 if not DEMO_MODE else "50%",
        style="height: 100%;",
        gap="3px",
    ),
    ui.tags.link(rel="stylesheet", href="styles.css"),
    #
    ##########  HEADER  ##########
    #
    ui.output_text("show_title", container=ui.h3),
    ui.output_code("show_query", placeholder=False).add_style(
        "max-height: 100px; overflow: auto;"
    ),
    #
    ##########  VALUE BOXES  ##########
    #
    ui.layout_columns(
        ui.value_box(
            "Total cells",
            ui.output_text("total_cell_counts"),
            showcase=fa.icon_svg("calculator"),
        ),
        ui.value_box(
            "Cell Proliferation Score (%Ki67+)", ui.output_text("average_ki67"), 
            showcase=fa.icon_svg("ruler")
        ),
        fill=False,
    ),
    ui.layout_columns(
        #
        ##########  DATA TABLE  ##########
        #
        ui.card(
            ui.card_header("Cell data, aggregated per ROI"),
            ui.output_data_frame("table"),
            full_screen=True,
        ),
        #
        ##########  HISTOGRAM  ##########
        #
        ui.card(
            ui.card_header(
                "Cell count per Image",
                ui.span(
                    ui.input_action_link(
                        "interpret_histogram",
                        icon_explain,
                        class_="me-3",
                        style="color: inherit;",
                        aria_label="Explain histogram",
                    ),
                    ui.popover(
                        icon_ellipsis,
                        ui.input_radio_buttons(
                            "histogram_color",
                            None, 
                            ['Class', 'Name', 'PD-L1 Status'],
                            inline=True,
                        ),
                        title="Color by variable",
                        placement="top",
                    ),
                ),
                class_="d-flex justify-content-between align-items-center",
            ),
            output_widget("cell_count_histogram"),
            full_screen=True,
        ),
#         ),
#         col_widths=[6, 12],
    ),
    title="Tumor Microenvironment",
    fillable=True,
)


def server(input, output, session):

    #
    ##########  REACTIVE STATE  ##########
    #

    current_query = reactive.Value("")
    current_title = reactive.Value("")
    messages = [query.system_prompt(cells_df, "cells")]

    @reactive.calc
    def cell_data():
        if current_query() == "":
            return cells_df
        return duckdb.query(current_query()).df()

    #
    ##########  HEADER OUTPUTS  ##########
    #

    @render.text
    def show_title():
        return current_title()

    @render.text
    def show_query():
        return current_query()

    #
    ##########  VALUE BOX OUTPUTS  ##########
    #

    @render.text
    def total_cell_counts():
        return str(cell_data().shape[0])

    @render.text
    def average_ki67():
        df = cell_data()
        pct_ki67_positive = df['Name'].value_counts(normalize=True, dropna=False)['Ki67']
        return f"{pct_ki67_positive:.1%}"

    #
    ##########  DATA TABLE  ##########
    #

    @render.data_frame
    def table():
        # df = cell_data()
        # agg_df = df.groupby(['Image', 'Parent', 'Class']).size().reset_index(name='Count')
        return render.DataGrid(cell_data())

    #
    ##########  HISTOGRAM  ##########
    #

    @render_plotly
    def cell_count_histogram():
        color = input.histogram_color()
        fig = px.histogram(
            cell_data(),
            x="Class", 
            color=color
        )
        return fig

    @reactive.effect
    @reactive.event(input.interpret_histogram)
    async def interpret_histogram():
        await explain_plot(
            input.model(), [*messages], cell_count_histogram.widget, toolbox=toolbox
        )

    
    #
    ##########  SIDE BOT  ##########
    #

    chat = ui.Chat(
        "chat",
        messages=[{"role": "assistant", "content": greeting}],
        tokenizer=None,
    )

    @chat.on_user_submit
    async def perform_chat():
        with reactive.isolate():
            chat_task(input.model(), messages, chat.user_input())

    @reactive.extended_task
    async def chat_task(model, messages, user_input):
        try:
            stream = query.perform_query(
                messages, user_input, model=model, toolbox=toolbox
            )
            return stream
        except Exception as e:
            traceback.print_exc()
            return f"**Error**: {e}", None, None

    @reactive.effect
    async def on_chat_complete():
        stream = chat_task.result()
        await chat.append_message_stream(stream)

    async def update_filter(query, title):
        async with reactive.lock():
            current_query.set(query)
            current_title.set(title)
            await reactive.flush()

    @tool
    async def update_dashboard(
        query: Annotated[str, "A DuckDB SQL query; must be a SELECT statement, or \"\"."],
        title: Annotated[
            str,
            "A title to display at the top of the data dashboard, summarizing the intent of the SQL query.",
        ],
    ):
        """Modifies the data presented in the data dashboard, based on the given SQL query, and also updates the title."""

        # Verify that the query is OK; throws if not
        if query != "":
            await query_db(query)

        await update_filter(query, title)

    @tool(name="query")
    async def query_db(
        query: Annotated[str, "A DuckDB SQL query; must be a SELECT statement."]
    ):
        """Perform a SQL query on the data, and return the results as JSON."""
        return duckdb.query(query).to_df().to_json(orient="records")

    toolbox = Toolbox(update_dashboard, query_db)


app = App(app_ui, server, static_assets=here / "www")