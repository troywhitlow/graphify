Attribute VB_Name = "Utilities"
Option Explicit

Public Function Add(ByVal a As Long, ByVal b As Long) As Long
    Add = a + b
End Function

Public Sub PrintBanner()
    Debug.Print "Utilities module loaded"
End Sub

Private Function InternalHelper() As String
    InternalHelper = "helper"
End Function
