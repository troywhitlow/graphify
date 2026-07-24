VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
  Persistable = 0  'NotPersistable
  DataBindingBehavior = 0  'vbNone
END
Attribute VB_Name = "CustomerAccount"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit

Implements IPersistable

Private mBalance As Currency

Public Property Get Balance() As Currency
    Balance = mBalance
End Property

Public Property Let Balance(ByVal value As Currency)
    mBalance = value
End Property

Public Sub Deposit(ByVal amount As Currency)
    mBalance = mBalance + amount
End Sub

Public Function Withdraw(ByVal amount As Currency) As Boolean
    If amount <= mBalance Then
        mBalance = mBalance - amount
        Withdraw = True
    End If
End Function
