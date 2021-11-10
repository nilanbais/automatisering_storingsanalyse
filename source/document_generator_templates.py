"""
Class voor het genereren van documenten met behulp van templates.

Voor extra inforamtie over docxtpl, zie: https://docxtpl.readthedocs.io/en/latest
"""
from source.storingsanalyse import StoringsAnalyse
import docxtpl
import os
import pandas as pd
import numpy as np


class DocumentGenerator:

    def __init__(self, project: str, api_key: str, rapport_type: str, quarter: str, year: str, staging_file_name: str = None) -> None:
        self.sa = StoringsAnalyse(project, api_key, rapport_type, quarter, year, staging_file_name)

        self._default_export_file_name = f"{self.sa.quarter}_{self.sa.year}_storingsanalyse_tekst.docx"
        self._default_export_file_name_appendix = f"{self.sa.quarter}_{self.sa.year}_storingsanalyse_bijlage.pdf"

        self.template_folder = "resources\\document_templates"
        self.rendered_document_folder = "resources\\temp"
        self.default_export_location = "documents\\generated_documents"

    def create_rendered_document(self, data_package: dict, template_file: str, addition_to_filename: str = None) -> None:
        if addition_to_filename:
            template_file_name, doc_extention = template_file.split('.')
            save_filename = "{0}\\render_{1}_{2}.{3}".format(self.rendered_document_folder, template_file_name, addition_to_filename, doc_extention)
        else:
            save_filename = "{0}\\render_{1}".format(self.rendered_document_folder, self._default_export_file_name)

        doc = docxtpl.DocxTemplate(os.path.join(self.template_folder, template_file))
        doc.render(data_package)
        doc.save(save_filename)

    @staticmethod
    def month_list_to_string(month_list: list) -> str:
        month_string = '{}'.format(month_list[0])
        if len(month_list) > 1:
            for i in range(1, len(month_list)):
                month_string += ' en {}'.format(month_list[i])
        return month_string

    def filter_staging_data(self, ntype: str, column_to_filter: str, threshold: int) -> list:
        """
        filters the given column of the staging_data and returns a list of objects that is higher or equal to
        the given threshold.
        """
        staging_data_ntype = self.sa.return_ntype_staging_file_object(ntype=ntype)
        staging_data_grouped = staging_data_ntype[column_to_filter].value_counts()

        objects_to_handle = list()
        for item in staging_data_grouped.index:
            if staging_data_grouped[item] < threshold:
                continue
            objects_to_handle.append(item)

        return objects_to_handle

    def get_assets_to_handle(self, threshold: int, ntype: str) -> list:
        assets_to_handle = self.filter_staging_data(ntype=ntype, column_to_filter='asset nummer', threshold=threshold)
        return assets_to_handle

    def get_subsystems_to_handle(self, threshold: int, ntype: str) -> list:
        subsystems_to_handle = self.filter_staging_data(ntype=ntype, column_to_filter='sbs', threshold=threshold)
        return subsystems_to_handle
    
    def get_data_h3(self, ntype: str, threshold: int) -> dict:

        # Set input data to variable
        staging_file_data = self.sa.return_ntype_staging_file_object(ntype=ntype)
        meta_data_ntype = self.sa.metadata.return_ntype_meta_object(ntype=ntype)

        previous_quarter_q, previous_quarter_year = self.sa.get_previous_quarter_q_year(quarter=self.sa.quarter,
                                                                                        year=self.sa.year)

        total_notifications = len(staging_file_data)

        staging_file_data_groupby_month = staging_file_data['month_number'].value_counts()

        monthly_avg_current_quarter = sum(staging_file_data_groupby_month) / len(staging_file_data_groupby_month)

        # quarterly_avg_from_meta
        quarterly_avg_from_meta = self.sa.metadata.avg_quarterly(dictionary=meta_data_ntype)

        # gives the min and max number of notifications
        max_monthly_notifications = max(staging_file_data_groupby_month)
        min_monthly_notifications = min(staging_file_data_groupby_month)

        # gives the month names of those with min and max notifications
        month_max_notifications = self.sa.get_min_max_months(staging_file_data_groupby_month.to_dict(), min_max='max')
        month_min_notifications = self.sa.get_min_max_months(staging_file_data_groupby_month.to_dict(), min_max='min')
        
        multiple_months_max = True if len(month_max_notifications) > 1 else False
        multiple_months_min = True if len(month_min_notifications) > 1 else False

        month_max_notifications = self.month_list_to_string(month_max_notifications)
        month_min_notifications = self.month_list_to_string(month_min_notifications)

        # quarter comparisons
        monthlist = self.sa.metadata.get_keys(dictionary=meta_data_ntype, containing_quarter=[self.sa.quarter],
                                              containing_year=[self.sa.prev_year])
        ntype_gefilterd = self.sa.metadata.filter_dictionary_keys(dictionary=meta_data_ntype, keys=monthlist)
        total_notifications_prev_year = self.sa.metadata.sum_values(ntype_gefilterd)

        difference_curr_year_prev_year = total_notifications - total_notifications_prev_year
        bool_diff_year_negative = True if difference_curr_year_prev_year < 0 else False

        # Aantal ntype in voorgaande q
        monthlist = self.sa.metadata.get_keys(dictionary=meta_data_ntype, containing_quarter=[previous_quarter_q],
                                              containing_year=[previous_quarter_year])
        ntype_gefilterd = self.sa.metadata.filter_dictionary_keys(dictionary=meta_data_ntype, keys=monthlist)
        total_notifications_prev_q = self.sa.metadata.sum_values(ntype_gefilterd)

        difference_curr_q_prev_q = total_notifications - total_notifications_prev_q
        bool_diff_q_negative = True if difference_curr_q_prev_q < 0 else False

        sbs_count = staging_file_data.loc[:, 'sbs'].value_counts()
        sbs_numbers_to_process = [x for x in sbs_count.index if sbs_count.at[x] >= threshold]

        count_unique_sbs_numbers = len(sbs_numbers_to_process)
        notification_count_unique_sbs_numbers = sum(sbs_count[sbs_numbers_to_process])

        # percentage notifications unique sbs numbers against total notifications
        special_percentage = round((notification_count_unique_sbs_numbers / total_notifications) * 100, 2)

        # counts per ntype
        ntype_storingen = True if ntype == 'storingen' else False
        count_storingen = str()
        count_preventief = str()
        count_incident = str()
        count_onterecht = str()
        if not ntype_storingen:
            staging_file_data_groupby_ntype = staging_file_data.loc[:, 'type melding (Storing/Incident/Preventief/Onterecht)'].value_counts()
            count_storingen = staging_file_data_groupby_ntype['Storing']
            count_preventief = staging_file_data_groupby_ntype['Preventief']
            count_incident = staging_file_data_groupby_ntype['Incident']
            count_onterecht = staging_file_data_groupby_ntype['Onterecht']

        rows_to_process = []
        for sbs in sbs_numbers_to_process:
            count_notifications = sbs_count[sbs]
            sbs_name = self.sa.get_breakdown_description(sbs_lbs=sbs)
            row_percentage = round((count_notifications/sum(sbs_count)) * 100, 2)
            row = {"sbs_name": str(sbs_name),
                   "count_notifications": str(count_notifications),
                   "percentage": str(row_percentage)}
            rows_to_process.append(row)

        # All the values need to be dtype str to be able to be rendered into the template
        data_package = {"ntype": str(ntype.lower()),
                        "ntype_storingen": ntype_storingen,  # boolean
                        "start_date_project": str(self.sa.project_start_date),
                        "q_current": str(self.sa.quarter),
                        "year_current": str(self.sa.year),
                        "year_prev": str(self.sa.prev_year),
                        "previous_quarter_q": str(previous_quarter_q),
                        "previous_quarter_year": str(previous_quarter_year),
                        "threshold": str(threshold),
                        "total_notifications": str(total_notifications),
                        "month_name_highest": str(month_max_notifications),
                        "month_name_lowest": str(month_min_notifications),
                        "max_monthly_notifications": str(max_monthly_notifications),
                        "multiple_months_max": multiple_months_max,  # boolean
                        "multiple_months_min": multiple_months_min,  # boolean
                        "min_monthly_notifications": str(min_monthly_notifications),
                        "monthly_avg_notifications": str(monthly_avg_current_quarter),
                        "count_unique_sbs_numbers": str(count_unique_sbs_numbers),
                        "notifications_unique_sbs_numbers": str(notification_count_unique_sbs_numbers),
                        "percentage_unique_sbs_numbers_to_total": str(special_percentage),
                        "count_storingen": str(count_storingen),
                        "count_preventief": str(count_preventief),
                        "count_incident": str(count_incident),
                        "count_onterecht": str(count_onterecht),
                        "total_notifications_prev_year": str(total_notifications_prev_year),
                        "difference_curr_year_prev_year": str(abs(difference_curr_year_prev_year)),
                        "difference_year_negative": bool_diff_year_negative,  # boolean
                        "total_notifications_prev_q": str(total_notifications_prev_q),
                        "difference_curr_q_prev_q": str(abs(difference_curr_q_prev_q)),
                        "difference_q_negative": bool_diff_q_negative,  # boolean
                        "quarterly_avg_from_meta": str(quarterly_avg_from_meta),
                        "rows_to_process": rows_to_process,
                        }

        return data_package

    def get_poo_table_data(self, poo_type: str) -> list:
        poo_type_string = self.sa.metadata.return_poo_type_string(poo_type)

        poo_type_count = self.sa.meldingen[poo_type_string].value_counts(dropna=False).to_dict()

        meta_poo_type = self.sa.metadata.poo_data()[poo_type_string.split(' ')[0]]

        poo_type_avg_table = self.sa.metadata.poo_avg_table(poo_dictionary=meta_poo_type,poo_type=poo_type)

        poo_beschrijvingen = self.sa.metadata.contract_info()['POO_codes']

        lines_list = []
        for code in self.sa.metadata.return_poo_code_list(poo_type):
            poo_code_count = 0
            for quarter in meta_poo_type.keys():
                if code in meta_poo_type[quarter].keys():
                    poo_code_count += self.sa.metadata.sum_values(dictionary=meta_poo_type[quarter], keys=[code])

            poo_count = poo_type_count[code] if code in list(poo_type_count.keys()) else 0
            poo_total = poo_code_count + poo_count

            line_dictionary = {"poo_code": str(code),
                               "poo_beschrijving": str(poo_beschrijvingen[code]),
                               "poo_count": str(poo_count),
                               "poo_total": str(poo_total),
                               "poo_avg": str(poo_type_avg_table[code])}

            lines_list.append(line_dictionary)

        return lines_list

    def get_data_h4_conclusie(self) -> dict:
        staging_file_data = self.sa.return_ntype_staging_file_object(ntype='meldingen')

        asset_number_value_counts = staging_file_data['asset nummer'].value_counts(dropna=False)
        orders_without_asset = max(asset_number_value_counts[asset_number_value_counts.index.isnull()])
        # max() in above statement to extract the single number from the pd.Series()

        p_rows_to_process = self.get_poo_table_data(poo_type='probleem')
        c_rows_to_process = self.get_poo_table_data(poo_type='oorzaak')
        s_rows_to_process = self.get_poo_table_data(poo_type='oplossing')

        data_package = {"orders_without_asset": orders_without_asset,
                        "p_rows_to_process": p_rows_to_process,
                        "c_rows_to_process": c_rows_to_process,
                        "s_rows_to_process": s_rows_to_process}

        return data_package

    def get_data_h4_subsystem(self, subsystem: str, ntype: str = 'storingen', ) -> dict:
        # default is 'storingen' omdat deze analyse standaar op de storingen wordt uitgevoerd
        staging_data_ntype = self.sa.return_ntype_staging_file_object(ntype=ntype)
        staging_data_groupby_sbs = staging_data_ntype.groupby('sbs')

        ntype_storingen = True if ntype == 'storingen' else False

        subsystem_data = staging_data_groupby_sbs.get_group(str(subsystem))

        total_notifications_subsystem = len(subsystem_data)

        subsystem_data_groupby_month = subsystem_data['month_number'].value_counts()

        monthly_avg_notifications_subsystem = sum(subsystem_data_groupby_month) / 3  # 3 months in a quarter

        # gives the min and max number of notifications
        max_monthly_notifications = max(subsystem_data_groupby_month)
        min_monthly_notifications = min(subsystem_data_groupby_month)

        month_max_notifications = self.sa.get_min_max_months(subsystem_data_groupby_month.to_dict(), min_max='max')
        month_min_notifications = self.sa.get_min_max_months(subsystem_data_groupby_month.to_dict(), min_max='min')

        multiple_months_max = True if len(month_max_notifications) > 1 else False
        multiple_months_min = True if len(month_min_notifications) > 1 else False

        month_max_notifications = self.month_list_to_string(month_max_notifications)
        month_min_notifications = self.month_list_to_string(month_min_notifications)

        # avg_from_meta
        subsystem_notifications_from_meta = self.sa.metadata.get_di_dict(di=str(subsystem), notification_type=ntype)
        ntype_meta_length = len(self.sa.metadata.return_ntype_meta_object(ntype=ntype))

        monthly_avg_from_meta_subsystem = sum(subsystem_notifications_from_meta.values()) / ntype_meta_length

        quarterly_avg_from_meta_subsystem = "WAARDE IS NOG NIET BEREKEND"

        subsystem_name = self.sa.get_breakdown_description(sbs_lbs=str(subsystem))

        data_package = {"ntype": str(ntype.lower()),
                        "ntype_storingen": ntype_storingen,  # boolean
                        "subsystem_number": str(subsystem),
                        "subsystem_name": subsystem_name,
                        "start_date_project": str(self.sa.project_start_date),
                        "q_current": str(self.sa.quarter),
                        "q_prev": str(self.sa.prev_quarter),
                        "year_current": str(self.sa.year),
                        "year_prev": str(self.sa.prev_year),
                        "total_notifications_subsystem": total_notifications_subsystem,
                        "monthly_avg_notifications_subsystem": monthly_avg_notifications_subsystem,
                        "month_name_highest": str(month_max_notifications),
                        "month_name_lowest": str(month_min_notifications),
                        "max_monthly_notifications": str(max_monthly_notifications),
                        "min_monthly_notifications": str(min_monthly_notifications),
                        "multiple_months_max": multiple_months_max,  # boolean
                        "multiple_months_min": multiple_months_min,  # boolean
                        "quarterly_avg_from_meta_subsystem": quarterly_avg_from_meta_subsystem,
                        "monthly_avg_from_meta_subsystem": monthly_avg_from_meta_subsystem,
                        }

        return data_package

    def get_data_h5_algemeen(self, threshold: int, ntype: str = 'meldingen') -> dict:
        staging_data_ntype = self.sa.return_ntype_staging_file_object(ntype=ntype)
        staging_data_groupby_asset = staging_data_ntype['asset nummer'].value_counts(dropna=False).to_dict()

        total_notifications = sum(staging_data_groupby_asset.values())

        asset_descriptions = {staging_data_ntype['asset nummer'][index]: staging_data_ntype['asset beschrijving'][index]
                              for index in range(staging_data_ntype.shape[0])}

        nan_notifications = 0
        assets_to_handle = dict()
        for key, value in staging_data_groupby_asset.items():
            if key is np.NaN:
                nan_notifications = value
                continue
            elif value >= threshold:
                assets_to_handle[key] = value

        assets_to_handle_count = len(assets_to_handle)

        rows_to_process = list()
        for asset in list(assets_to_handle.keys()):
            sbs_number = staging_data_ntype['sbs'][staging_data_ntype['asset nummer'] == asset].unique()[0]  # returns one number
            sbs_name = self.sa.get_breakdown_description(sbs_lbs=str(sbs_number))

            asset_description = asset_descriptions[asset]

            notification_count = assets_to_handle[asset]

            row = {"sbs_name": str(sbs_name),
                   "asset_description": str(asset_description),
                   "notification_count": str(notification_count)}
            rows_to_process.append(row)

        data_package = {"ntype": str(ntype),
                        "threshold": str(threshold),
                        "current_q": str(self.sa.quarter),
                        "current_year": str(self.sa.year),
                        "nan_notifications": str(nan_notifications),
                        "total_notifications": str(total_notifications),
                        "assets_to_handle_count": str(assets_to_handle_count),
                        "rows_to_process": rows_to_process,
                        }

        return data_package

    def get_data_h5_uitwerking_melding(self, asset_number: str, ntype: str = 'meldingen') -> dict:
        staging_data_ntype = self.sa.return_ntype_staging_file_object(ntype=ntype)
        poo_beschrijvingen = self.sa.metadata.contract_info()['POO_codes']

        asset_description = staging_data_ntype['asset beschrijving'][staging_data_ntype['asset nummer'] == asset_number].unique()[0]  # returns one number

        asset_notifications = staging_data_ntype[staging_data_ntype['asset nummer'] == asset_number]
        notification_count = asset_notifications.shape[0]

        rows_to_process = list()
        _asset_notification_dict = asset_notifications.to_dict()  # to enhance readability
        for idx in list(asset_notifications.index):
            workorder = _asset_notification_dict['werkorder'][idx]
            notification_type = _asset_notification_dict['type melding (Storing/Incident/Preventief/Onterecht)'][idx]
            problem_text = poo_beschrijvingen[_asset_notification_dict['probleem code'][idx]]
            cause_text = poo_beschrijvingen[_asset_notification_dict['oorzaak code'][idx]]
            solution_text = poo_beschrijvingen[_asset_notification_dict['oplossing code'][idx]]

            row_content = {"workorder": workorder,
                           "notification_type": notification_type,
                           "problem_text": problem_text,
                           "cause_text": cause_text,
                           "solution_text": solution_text}
            rows_to_process.append(row_content)

        data_package = {"ntype": ntype,
                        "asset_description": str(asset_description),
                        "notification_count": str(notification_count),
                        "rows_to_process": rows_to_process}
        return data_package

    def get_data_h5_conclusie(self, threshold: int, ntype: str = 'meldingen') -> dict:
        staging_data_ntype = self.sa.return_ntype_staging_file_object(ntype=ntype)

        # Onderstaand stuk is gekopieerd -> maak uiteindelijk een aparte method ervan
        staging_data_groupby_asset = staging_data_ntype['asset nummer'].value_counts(dropna=False).to_dict()
        assets_to_handle = dict()
        for key, value in staging_data_groupby_asset.items():
            if key is np.NaN:
                continue
            elif value >= threshold:
                assets_to_handle[key] = value
        assets_to_handle_count = len(assets_to_handle)

        data_package = {"threshold": threshold,
                        "assets_to_handle_count": assets_to_handle_count}

        return data_package

    def build_text_document(self, threshold: int) -> None:
        data_package_h3 = {"h3_paragraphs": [self.get_data_h3(ntype=type, threshold=threshold)
                                             for type in ['meldingen', 'storingen']]}

        data_package_h4 = {"algemeen_h4": self.get_data_h4_conclusie(),
                           "subsystems_to_process": [self.get_data_h4_subsystem(subsystem=subsystem, ntype='storingen')
                                                     for subsystem in self.get_subsystems_to_handle(threshold=threshold,
                                                                                                    ntype='storingen')]}

        data_package_h5 = {"algemeen_h5": self.get_data_h5_algemeen(threshold=threshold),
                           "assets_to_process": [self.get_data_h5_uitwerking_melding(asset_number=asset)
                                                 for asset in self.get_assets_to_handle(threshold=threshold,
                                                                                        ntype='meldingen')],
                           "conclusie_h5": self.get_data_h5_conclusie(threshold=3)}

        storingsanalyse_data_package = {**data_package_h3, **data_package_h4, **data_package_h5}

        self.create_rendered_document(data_package=storingsanalyse_data_package,
                                      template_file='storingsanalyse_template.docx')

    def build_appendix(self, threshold: int = 0):
        print('Creating file ' + self._default_export_file_name_appendix)

        _file_name = self._default_export_file_name_appendix

        #
        # Aantal meldingen per deelinstallatie
        #
        title = 'Aantal meldingen per deelinstallatie'
        df = self.sa.return_ntype_staging_file_object(ntype='meldingen')
        time_range = [min(df['rapport datum']), max(df['rapport datum'])]
        available_categories = self.sa.metadata.contract_info()['aanwezige_deelinstallaties']

        categories, prepped_data = self.sa.prep(df, time_range, available_categories,
                                                time_key='rapport datum', category_key='sbs')

        readable_labels = [self.sa.prettify_time_label(label) for label in self.sa.last_seen_bin_names]
        self.sa.plot(input_data=prepped_data, plot_type='stacked',
                     category_labels=categories, bin_labels=readable_labels, title=title)

        summary_data = self.sa.prep_summary(df, time_range, available_categories, time_key='rapport datum',
                                            category_key='sbs')
        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        #
        # Aantal storingen per deelinstallatie
        #
        title = 'Aantal storingen per deelinstallatie'
        df = self.sa.return_ntype_staging_file_object(ntype='storingen')

        categories, prepped_data = self.sa.prep(df, time_range, available_categories,
                                                time_key='rapport datum', category_key='sbs')

        # needed to cover 'nan', else ValueError: shape mismatch: objects cannot be broadcast to a single shape
        readable_labels = [self.sa.prettify_time_label(label) for label in self.sa.last_seen_bin_names]
        self.sa.plot(input_data=prepped_data, plot_type='stacked',
                     category_labels=categories, bin_labels=readable_labels,
                     title=title)

        summary_data = self.sa.prep_summary(df, time_range, available_categories, time_key='rapport datum',
                                            category_key='sbs')
        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        #
        # Aantal onterechte meldingen per deelinstallatie
        #
        title = 'Aantal onterechte meldingen per deelinstallatie'
        df = self.sa.return_ntype_staging_file_object(ntype='onterecht')

        categories, prepped_data = self.sa.prep(df, time_range, available_categories,
                                                time_key='rapport datum', category_key='sbs')

        readable_labels = [self.sa.prettify_time_label(label) for label in self.sa.last_seen_bin_names]

        self.sa.plot(input_data=prepped_data, plot_type='stacked',
                     category_labels=categories, bin_labels=readable_labels,
                     title=title)

        summary_data = self.sa.prep_summary(df, time_range, available_categories, time_key='rapport datum',
                                            category_key='sbs')
        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        #
        # Totaal aantal meldingen preventief per deelinstallatie
        #
        title = 'Totaal aantal preventieve meldingen per deelinstallatie'
        df = self.sa.return_ntype_staging_file_object(ntype='preventief')

        categories, prepped_data = self.sa.prep(df, time_range, available_categories,
                                                time_key='rapport datum', category_key='sbs')

        readable_labels = [self.sa.prettify_time_label(label) for label in self.sa.last_seen_bin_names]

        self.sa.plot(input_data=prepped_data, plot_type='stacked',
                     category_labels=categories, bin_labels=readable_labels,
                     title=title)

        summary_data = self.sa.prep_summary(df, time_range, available_categories, time_key='rapport datum',
                                            category_key='sbs')
        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        #
        # Aantal incidenten per deelinstallatie
        #
        title = 'Aantal incidenten per deelinstallatie'
        df = self.sa.return_ntype_staging_file_object(ntype='incident')

        categories, prepped_data = self.sa.prep(df, time_range, available_categories,
                                                time_key='rapport datum', category_key='sbs')

        readable_labels = [self.sa.prettify_time_label(label) for label in self.sa.last_seen_bin_names]

        self.sa.plot(input_data=prepped_data, plot_type='stacked',
                     category_labels=categories, bin_labels=readable_labels,
                     title=title)

        summary_data = self.sa.prep_summary(df, time_range, available_categories, time_key='rapport datum',
                                            category_key='sbs')
        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        # todo: tijden dynamisch maken
        # Vergelijking voorgaande kwartaal met huidinge kwartaal
        #
        # Meldingen
        #
        title = 'SPECIFICEER TITEL'
        categories, prepped_data = self.sa.prep(self.sa.metadata.unsaved_updated_meta['meldingen'],
                                                time_range=['10-2020', '03-2021'],
                                                available_categories=available_categories,
                                                time_key='rapport datum',
                                                category_key='sbs',
                                                bin_size='quarter')

        self.sa.plot(input_data=prepped_data,
                     plot_type='side-by-side',
                     category_labels=categories,
                     bin_labels=self.sa.last_seen_bin_names,
                     title=title)

        summary_data = self.sa.prep_summary(self.sa.metadata.unsaved_updated_meta['meldingen'],
                                            time_range=['10-2020', '03-2021'],
                                            available_categories=available_categories,
                                            bin_size='quarter')

        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        #
        # Storingen
        #
        title = 'SPECIFICEER TITEL'
        categories, prepped_data = self.sa.prep(self.sa.metadata.unsaved_updated_meta['storingen'],
                                                time_range=['10-2020', '03-2021'],
                                                available_categories=available_categories,
                                                time_key='rapport datum',
                                                category_key='sbs',
                                                bin_size='quarter')

        self.sa.plot(input_data=prepped_data,
                     plot_type='side-by-side',
                     category_labels=categories,
                     bin_labels=self.sa.last_seen_bin_names,
                     title=title)

        summary_data = self.sa.prep_summary(self.sa.metadata.unsaved_updated_meta['storingen'],
                                            time_range=['10-2020', '03-2021'],
                                            available_categories=available_categories,
                                            bin_size='quarter')

        self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                             data=list(summary_data.values()),
                             title=title)

        #
        # Verdeling type meldingen per deelinstallatie
        #
        title = 'Verdeling type meldingen voor DI {}'
        df = self.sa.return_ntype_staging_file_object(ntype='meldingen')
        df_groupby_sbs = df.groupby(['sbs'])

        # unieke types vastlegen
        unique_types = df.loc[:, 'type melding (Storing/Incident/Preventief/Onterecht)'].unique()

        # cols kan voor een sandbox tool variabel gemaakt worden.
        cols = ['type melding (Storing/Incident/Preventief/Onterecht)', 'month_number']

        sbs_count = df.loc[:, 'sbs'].value_counts()
        to_process = [x for x in sbs_count.index if sbs_count.at[x] >= threshold]
        for di_num in to_process:
            categories, prepped_data = self.sa.prep(df_groupby_sbs.get_group(di_num),
                                                    time_range=['10-2020', '03-2021'],
                                                    available_categories=unique_types,
                                                    time_key='rapport datum',
                                                    category_key='type melding (Storing/Incident/Preventief/Onterecht)')

            self.sa.plot(input_data=prepped_data,
                         plot_type='stacked',
                         category_labels=categories,
                         bin_labels=[self.sa.prettify_time_label(label) for label in self.sa.last_seen_bin_names],
                         title=title.format(di_num))

            summary_data = self.sa.prep_summary(df_groupby_sbs.get_group(di_num),
                                                time_range=['10-2020', '03-2021'],
                                                available_categories=unique_types,
                                                time_key='rapport datum',
                                                category_key='type melding (Storing/Incident/Preventief/Onterecht)')

            self.sa.plot_summary(x_labels=[self.sa.prettify_time_label(label) for label in summary_data.keys()],
                                 data=list(summary_data.values()),
                                 title=title.format(di_num))

        #
        # Exporting appendix
        #
        self.sa.export_graphs(filename=os.path.join(self.default_export_location, _file_name))

        print('Finished.')


def main():
    dg = DocumentGenerator(project="Coentunnel-tracé",
                           rapport_type="Kwartaalrapportage",
                           quarter="Q2",
                           year="2021",
                           api_key="bWF4YWRtaW46R21iQ1dlbkQyMDE5",
                           staging_file_name='validating_input_data.xlsx')

    dg.build_appendix(threshold=3)


if __name__ == '__main__':
    main()
