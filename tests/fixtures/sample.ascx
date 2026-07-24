<%@ Control Language="VB" CodeFile="Footer.ascx.vb" Inherits="Acme.Web.Footer" %>
<div class="footer">
    <asp:Label ID="lblYear" runat="server" />
    <script runat="server">
        Public Sub Page_Init(sender As Object, e As EventArgs)
            RenderYear()
        End Sub

        Private Sub RenderYear()
            lblYear.Text = "2026"
        End Sub
    </script>
</div>
