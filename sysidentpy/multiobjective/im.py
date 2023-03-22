import numpy as np
from sysidentpy.model_structure_selection import FROLS


class IM(FROLS):
    """Multi-purpose estimation of parameters

    Parameters
    ----------
    Static_Gain : bool, default=True
        Presence of data referring to static gain.
    Static_Function : bool, default=True
        Presence of data regarding static function.
    Y_static : array-like of shape = n_samples_static_function, default = ([0])
        Output of static function.
    X_static : array-like of shape = n_samples_static_function, default = ([0])
        Static function input.
    Gain : array-like of shape = n_samples_static_gain, default = ([0])
        Static gain input.
    y_train : array-like of shape = n_samples, defalult = ([0])
        The target data used in the identification process.
    PSI : ndarray of floats, default = ([[0],[0]])
        Matrix of static regressors.
    n_inputs : int, default=1
        Number of entries.
    non_degree : int, default=2
        Degree of nonlinearity.
    model_type : string, default='NARMAX'
        Model type.
    final_model : ndarray, default = ([[0],[0]])
        Template code.
    w : ndarray, default = ([[0],[0]])
        Matrix with weights.
    """
    def __init__(self,
                 Static_Gain=True,
                 Static_Function=True,
                 Y_static=np.zeros(1),
                 X_static=np.zeros(1),
                 Gain=np.zeros(1),
                 y_train=np.zeros(1),
                 PSI=np.zeros((1, 1)),
                 n_inputs=1,
                 non_degree=2,
                 model_type='NARMAX',
                 final_model=np.zeros((1, 1)),
                 W=np.zeros((1, 1))
                 ):
        self.Static_Gain = Static_Gain
        self.Static_Function = Static_Function
        self.psi = PSI
        self._n_inputs = n_inputs
        self.non_degree = non_degree
        self.model_type = model_type
        self.Y_static = Y_static
        self.X_static = X_static
        self.final_model = final_model
        self.gain = Gain
        self.y_train = y_train
        self.W = W
    def R_qit(self):
        """Assembly of the R matrix and ordering of the q_it."""
        N = []
        for i in range(0, self._n_inputs):
            N.append(1)
        qit = self.regressor_space(
            self.non_degree, N, 1, self._n_inputs, self.model_type
        )//1000
        # (41, 50) -> Gerando a matriz de mapeamento linear
        model = self.final_model//1000
        R = np.zeros((np.shape(qit)[0], np.shape(model)[0]))
        b = []
        for i in range(0, np.shape(qit)[0]):
            for j in range(0, np.shape(model)[0]):
                if (qit[i, :] == model[j, :]).all():
                    R[i, j] = 1
            if sum(R[i, :]) == 0:
                b.append(i)
        R = np.delete(R, b, axis=0)
        # (52, 67) -> é montada a matriz dos regressores estáticos
        qit = np.delete(qit, b, axis=0)
        return R, qit
               
    def static_function(self):
        """Matrix of static regressors."""
        R, qit = self.R_qit()
        a = np.shape(qit)[0]
        N_aux = np.zeros((a, int(np.max(qit))))
        for k in range(0, int(np.max(qit))):
            for i in range(0, np.shape(qit)[0]):
                for j in range(0, np.shape(qit)[1]):
                    if k + 1 == qit[i, j]:
                        N_aux[i, k] = 1 + N_aux[i, k]
        qit = N_aux
        Q = np.zeros((len(self.Y_static), len(qit)))
        for i in range(0, len(self.Y_static)):
            for j in range(0, len(qit)):
                Q[i, j] = self.Y_static[i, 0]**(qit[j, 0])
                for k in range(0, self._n_inputs):
                    Q[i, j] = Q[i, j]*self.X_static[i, k]**(qit[j, 1+k])
        return Q.dot(R) 

    def static_gain(self):
        """Matrix of static regressors referring to derivative."""
        R, qit = self.R_qit()
        H = np.zeros((len(self.Y_static), len(qit)))
        G = np.zeros((len(self.Y_static), len(qit)))
        for i in range(0, len(self.Y_static)):
            for j in range(1, len(qit)):
                if self.Y_static[i, 0] == 0:
                    H[i, j] = 0
                else:
                    H[i, j] = self.gain[i]*qit[j, 0]*self.Y_static[i, 0]\
                        **(qit[j, 0]-1)
                for k in range(0, self._n_inputs):
                    if self.X_static[i, k] == 0:
                        G[i, j] = 0
                    else:
                        G[i, j] = qit[j, 1+k]*self.X_static[i, k]\
                            **(qit[j, 1+k]-1)
        return (G+H).dot(R)
    
    def weights(self):
        """Weights givenwith each goal."""
        w1 = np.arange(0.01, 1.00, 0.05)
        w2 = np.arange(1.00, 0.01, -0.05)
        a1 = []
        a2 = []
        a3 = []
        for i in range(0, len(w1)):
            for j in range(0, len(w2)):
                if w1[i]+w2[j] <= 1:
                    a1.append(w1[i])
                    a2.append(w2[j])
                    a3.append(1 - (w1[i]+w2[j]))
        if self.Static_Gain != False and self.Static_Function != False:
            W = np.zeros((3, len(a1)))
            W[0, :] = a1
            W[1, :] = a2
            W[2, :] = a3
        else:
            W = np.zeros((2, len(a1)))
            W[0, :] = a2
            W[1, :] = np.ones(len(a1))-a2
        return W
    def multio(self):
        """Calculation of parameters via multi-objective techniques.
        Returns
        -------
        J : ndarray
            Matrix referring to the objectives.
        W : ndarray
            Matrix referring to weights.
        E : ndarray
            Matrix of the Euclidean norm.
        Array_theta : ndarray
            Matrix with parameters for each weight.
        HR : ndarray
            H matrix multiplied by R.
        QR : ndarray
            Q matrix multiplied by R.
        """
        if sum(self.W[:, 0]) != 1:
            W = self.weights()
        else:
            W = self.W
        E = np.zeros(np.shape(W)[1])
        Array_theta = np.zeros((np.shape(W)[1], np.shape(self.final_model)[0]))
        for i in range(0, np.shape(W)[1]):
            part1 = W[0, i]*(self.psi).T.dot(self.psi)
            part2 = W[0, i]*(self.psi.T).dot(self.y_train)
            w = 1
            if self.Static_Function == True:
                QR = self.static_function()
                part1 = W[w, i]*(QR.T).dot(QR) + part1
                part2 = part2 + (W[w, i]*(QR.T).dot(self.Y_static))\
                    .reshape(-1,1)
                w = w + 1
            if self.Static_Function == True:
                HR = self.static_gain()
                part1 = W[w, i]*(HR.T).dot(HR) + part1
                part2 = part2 + (W[w, i]*(HR.T).dot(self.gain)).reshape(-1,1)
                w = w+1
            if i == 0:
                J = np.zeros((w, np.shape(W)[1]))
            Theta = ((np.linalg.inv(part1)).dot(part2)).reshape(-1, 1)
            Array_theta[i, :] = Theta.T
            J[0, i] = (((self.y_train)-(self.psi.dot(Theta))).T).dot((self.y_train)\
                     -(self.psi.dot(Theta)))
            w = 1
            if self.Static_Gain == True:
                J[w, i] = (((self.gain)-(HR.dot(Theta))).T).dot((self.gain)\
                          -(HR.dot(Theta)))
                w = w+1
            if self.Static_Function == True:
                J[w, i] = (((self.Y_static)-(QR.dot(Theta))).T).dot((self.Y_static)-(QR.dot(Theta)))
        for i in range(0, np.shape(W)[1]):
            E[i] = np.linalg.norm(J[:, i]/np.max(J))
        return J/np.max(J), W, E, Array_theta, HR, QR