import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_calendar import calendar
from data_loader import load_data, apply_filters

st.set_page_config(page_title="Costco Spend Tracker - Receipts", page_icon="🧾", layout="wide")

receipts_df, warehouse_df, gas_df = load_data()

if receipts_df is None or receipts_df.empty:
    st.error("No database found. Please run `python process.py` first.")
    st.stop()

f_receipts, f_warehouse, f_gas = apply_filters(receipts_df, warehouse_df, gas_df)

st.header("Receipt Explorer")

if f_receipts.empty:
    st.info("No receipts found in this date range.")
else:
    receipt_options = f_receipts.sort_values("transaction_datetime", ascending=False).reset_index(
        drop=True
    )

    def format_receipt_label(row):
        date_str = row["transaction_datetime"].strftime("%b %d, %Y")
        return (
            f"{date_str} - {row['warehouse_name']} ({row['receipt_type']}) - ${row['total']:.2f}"
        )

    receipt_options["label"] = receipt_options.apply(format_receipt_label, axis=1)
    labels = receipt_options["label"].tolist()
    label_to_barcode = dict(zip(receipt_options["label"], receipt_options["transaction_barcode"]))
    barcode_to_label = dict(
        zip(receipt_options["transaction_barcode"], receipt_options["label"])
    )
    valid_barcodes = set(receipt_options["transaction_barcode"])

    # --- Session state: selected receipt (barcode is source of truth) ---
    if (
        "receipt_barcode" not in st.session_state
        or st.session_state["receipt_barcode"] not in valid_barcodes
    ):
        st.session_state["receipt_barcode"] = receipt_options.iloc[0]["transaction_barcode"]

    # Light fills + dark text so block-style events stay readable
    _GAS_BG = "#FFE4E6"
    _GAS_BORDER = "#FB7185"
    _GAS_TEXT = "#9F1239"
    _WH_BG = "#E0F2FE"
    _WH_BORDER = "#38BDF8"
    _WH_TEXT = "#0C4A6E"

    calendar_events = []
    for _, row in receipt_options.iterrows():
        is_gas = row["receipt_type"] == "GAS STATION"
        if is_gas:
            title = f"⛽ ${row['total']:.2f}"
            bg, border, fg = _GAS_BG, _GAS_BORDER, _GAS_TEXT
        else:
            title = f"🛒 ${row['total']:.2f}"
            bg, border, fg = _WH_BG, _WH_BORDER, _WH_TEXT

        barcode = row["transaction_barcode"]
        calendar_events.append(
            {
                "id": str(barcode),
                "title": title,
                "start": row["transaction_datetime"].isoformat(),
                "backgroundColor": bg,
                "borderColor": border,
                "textColor": fg,
            }
        )

    min_dt = receipt_options["transaction_datetime"].min()
    max_dt = receipt_options["transaction_datetime"].max()
    initial_date = max_dt.strftime("%Y-%m-%d")
    start_date = min_dt.replace(day=1).strftime("%Y-%m-%d")
    end_date = (max_dt + pd.DateOffset(months=1)).replace(day=1).strftime("%Y-%m-%d")
    valid_range = {"start": start_date, "end": end_date}

    calendar_options = {
        "headerToolbar": {
            "left": "prev",
            "center": "title",
            "right": "next",
        },
        "initialView": "dayGridMonth",
        "initialDate": initial_date,
        "validRange": valid_range,
        "eventDisplay": "block",
        # Hide leading/trailing days that belong to adjacent months
        "showNonCurrentDates": False,
        # Use 4–6 week rows as needed; avoid a blank 6th row when the month fits in 5
        "fixedWeekCount": False,
        # Taller month grid; receipt detail lives in the right column
        "height": 520,
        "displayEventTime": False,
    }

    calendar_css = """
    .fc { font-size: 0.82rem; }
    .fc-toolbar-title { font-size: 1.15rem !important; }
    .fc-button { font-size: 0.8rem !important; padding: 0.25em 0.5em !important; }
    .fc-daygrid-day-number { font-size: 0.75rem; }
    .fc-event-title { font-size: 0.72rem; }
    """

    cal_col, receipt_col = st.columns([1, 1])

    with cal_col:
        st.subheader("Pick a visit")
        st.caption("Choose from the list, then use the calendar to jump by day.")

        label_for_barcode = barcode_to_label[st.session_state["receipt_barcode"]]
        sel_index = labels.index(label_for_barcode) if label_for_barcode in labels else 0
        selected_label = st.selectbox(
            "Choose receipt",
            labels,
            index=sel_index,
        )
        st.caption("Or click an event on the calendar to open it on the right.")

        cal_state = calendar(
            events=calendar_events,
            options=calendar_options,
            custom_css=calendar_css,
            callbacks=["eventClick"],
            key="receipts_trip_calendar",
        )

    if cal_state and cal_state.get("callback") == "eventClick":
        ev = cal_state.get("eventClick", {}).get("event") or {}
        clicked_id = ev.get("id")
        if clicked_id is not None:
            clicked_barcode = str(clicked_id)
            if clicked_barcode in valid_barcodes:
                st.session_state["receipt_barcode"] = clicked_barcode
    else:
        st.session_state["receipt_barcode"] = label_to_barcode[selected_label]

    with receipt_col:
        barcode = st.session_state["receipt_barcode"]
        selected_row = receipt_options[receipt_options["transaction_barcode"] == barcode].iloc[0]
        is_gas = selected_row["receipt_type"] == "GAS STATION"

        st.markdown(f"### 🛒 Costco {selected_row['warehouse_name']}")
        st.caption(
            f"**Date:** {selected_row['transaction_datetime'].strftime('%B %d, %Y at %I:%M %p')} | "
            f"**Member:** {selected_row['user_name'].title()} | **Card:** {selected_row['tender_type']} "
            f"ending in {selected_row['account_number']} | **Barcode:** `{barcode}`"
        )

        s_col1, s_col2, s_col3 = st.columns(3)
        s_col1.metric("Total", f"${selected_row['total']:.2f}")
        s_col2.metric("Tax", f"${selected_row['taxes']:.2f}")
        if is_gas:
            s_col3.empty()
        else:
            item_count = len(f_warehouse[f_warehouse["transaction_barcode"] == barcode])
            s_col3.metric("Items", str(item_count))

        st.markdown("##### Items")

        if is_gas:
            items = f_gas[f_gas["transaction_barcode"] == barcode]

            display_df = items[["fuel_grade", "quantity_gallons", "unit_price", "amount"]].copy()
            display_df.columns = ["Fuel Grade", "Gallons", "Price/Gal", "Total"]

            display_df["Price/Gal"] = display_df["Price/Gal"].apply(lambda x: f"${x:.3f}")
            display_df["Total"] = display_df["Total"].apply(lambda x: f"${x:.2f}")

            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                height=(len(display_df) + 1) * 35 + 3,
            )

        else:
            items = f_warehouse[f_warehouse["transaction_barcode"] == barcode]

            display_df = items[
                [
                    "item_number",
                    "category",
                    "item_name",
                    "quantity",
                    "unit_price",
                    "discount_amount",
                    "fee_amount",
                    "is_taxed",
                    "true_total",
                ]
            ].copy()

            display_df["Unit price"] = display_df["unit_price"].apply(lambda x: f"${x:.2f}")
            display_df["Tax"] = display_df["is_taxed"].apply(
                lambda x: "N" if pd.isna(x) else ("Y" if x else "N")
            )
            display_df["Discount"] = display_df["discount_amount"].apply(
                lambda x: f"-${abs(float(x)):.2f}" if pd.notna(x) and float(x) < 0 else ""
            )
            display_df["CRV"] = display_df["fee_amount"].apply(
                lambda x: f"${x:.2f}" if x > 0 else ""
            )
            display_df["Amount"] = display_df["true_total"].apply(lambda x: f"${x:.2f}")

            display_df = display_df[
                [
                    "item_number",
                    "category",
                    "item_name",
                    "Unit price",
                    "Tax",
                    "quantity",
                    "Discount",
                    "CRV",
                    "Amount",
                ]
            ]
            display_df.columns = [
                "Item #",
                "Category",
                "Item name",
                "Unit price",
                "Tax",
                "Qty",
                "Discount",
                "CRV",
                "Amount",
            ]
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                height=(len(display_df) + 1) * 35 + 3,
            )

        if not is_gas:
            st.markdown("---")
            st.subheader("Spend by Category")
            cat_spend = items.groupby("category")["true_total"].sum().reset_index()
            cat_spend = cat_spend.sort_values("true_total", ascending=False)

            fig_cat = px.pie(cat_spend, values="true_total", names="category", hole=0.4)
            fig_cat.update_layout(margin=dict(t=20, b=20, l=0, r=0), height=320)
            fig_cat.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_cat, use_container_width=True)
