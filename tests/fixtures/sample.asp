<%@ Language="VBScript" %>
<!--#include file="header.inc" -->
<!--#include virtual="/shared/footer.asp" -->
<%
Class Account
    Private mName

    Public Function GetName()
        GetName = mName
    End Function

    Public Sub SetName(value)
        mName = value
    End Sub
End Class

Sub RenderPage()
    Dim conn
    Set conn = Server.CreateObject("ADODB.Connection")
    conn.Open GetConnString()
End Sub

Function GetConnString()
    GetConnString = "DSN=demo"
End Function
%>
<html><body><% RenderPage %></body></html>
