<%@ Page Language="C#" CodeBehind="sample.aspx.cs" Inherits="Acme.Web.SamplePage" %>
<%@ Import Namespace="System.Data" %>
<%@ Register TagPrefix="uc1" TagName="Footer" Src="~/Controls/Footer.ascx" %>
<!DOCTYPE html>
<html>
<body>
    <form runat="server">
        <asp:GridView ID="grid" runat="server" />
        <uc1:Footer runat="server" />
    </form>
    <script runat="server">
        protected void Page_Load(object sender, EventArgs e)
        {
            BindGrid();
        }

        private void BindGrid()
        {
            grid.DataBind();
        }
    </script>
</body>
</html>
