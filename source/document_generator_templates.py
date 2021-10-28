"""
Class voor het genereren van documenten met behulp van templates.

Voor extra inforamtie over docxtpl, zie: https://docxtpl.readthedocs.io/en/latest
"""
from source.storingsanalyse import StoringsAnalyse
import docxtpl
import os


class DocumentGenerator:

    def __init__(self, project: str, api_key: str, rapport_type: str, quarter: str, year: str, staging_file_name: str = None) -> None:
        self.sa = StoringsAnalyse(project, api_key, rapport_type, quarter, year, staging_file_name)

        self._default_export_file_name = f"TEST_{self.sa.quarter}_{self.sa.year}_storingsanalyse_tekst.docx"
        self._default_export_file_name_appendix = f"TEST_{self.sa.quarter}_{self.sa.year}_storingsanalyse_bijlage.pdf"

        self.template_folder = "resources\\document_templates"
        self.rendered_document_folder = "resources\\temp"
        self.default_export_location = "documents\\generated_documents"

    def create_rendered_document(self, data_package: dict, template_file: str) -> None:
        doc = docxtpl.DocxTemplate(os.path.join(self.template_folder, template_file))
        doc.render(data_package)
        doc.save("{0}\\render_{1}".format(self.rendered_document_folder, template_file))

    @staticmethod
    def month_list_to_string(month_list: list) -> str:
        month_string = '{}'.format(month_list[0])
        if len(month_list) > 1:
            for i in range(1, len(month_list)):
                month_string += ' en {}'.format(month_list[i])
        return month_string
    
    def get_data_h3(self, ntype: str, threshold: int) -> dict:

        # Set input data to variable
        staging_file_data = self.sa.return_ntype_staging_file_object(ntype=ntype)
        meta_data_ntype = self.sa.metadata.return_ntype_meta_object(ntype=ntype)

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
        monthlist = self.sa.metadata.get_keys(dictionary=meta_data_ntype, containing_quarter=[self.sa.prev_quarter],
                                              containing_year=[self.sa.prev_year])
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
                        "q_prev": str(self.sa.prev_quarter),
                        "year_current": str(self.sa.year),
                        "year_prev": str(self.sa.prev_year),
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
                        "difference_curr_year_prev_year": str(difference_curr_year_prev_year),
                        "difference_year_negative": bool_diff_year_negative,  # boolean
                        "total_notifications_prev_q": str(total_notifications_prev_q),
                        "difference_curr_q_prev_q": str(difference_curr_q_prev_q),
                        "difference_q_negative": bool_diff_q_negative,  # boolean
                        "quarterly_avg_from_meta": str(quarterly_avg_from_meta),
                        "rows_to_process": rows_to_process,
                        }

        return data_package

    def get_data_h4(self) -> dict:
        pass


def main():
    dg = DocumentGenerator(project="Coentunnel-tracé",
                           rapport_type="Kwartaalrapportage",
                           quarter="Q2",
                           year="2021",
                           api_key="bWF4YWRtaW46R21iQ1dlbkQyMDE5",
                           staging_file_name='validating_input_data.xlsx')

    data_package_h3 = dg.get_data_h3(ntype='meldingen', threshold=3)

    dg.create_rendered_document(data_package=data_package_h3,
                                template_file='h3_analyse_template.docx')


if __name__ == '__main__':
    main()

